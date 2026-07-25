"""Diagnostico de conectividade e disponibilidade das fontes externas.

Nao grava nada. Serve para descobrir, de uma rede especifica, qual espelho
ERDDAP responde e quais variaveis cada dataset realmente publica - em vez de
trocar de servidor no escuro.

Uso:
    python backend/manage.py testar_fontes
"""

import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from ingestao.certificados import diagnosticar, garantir_bundle_ca, interpretar
from ingestao.conectores.noaa_crw import VARIAVEIS_ERDDAP

# Espelhos conhecidos do produto Coral Reef Watch 5 km.
# Servidor e dataset andam em par - o mesmo produto tem id diferente em cada.
CANDIDATOS_NOAA = [
    (
        'PACIOOS',
        'https://pae-paha.pacioos.hawaii.edu/erddap',
        'dhw_5km',
        'Par que gerou os CSVs que o projeto ja tem.',
    ),
    (
        'NOAA CoastWatch',
        'https://coastwatch.noaa.gov/erddap',
        'noaacrwdhwDaily',
        'Espelho oficial da NOAA.',
    ),
    (
        'NOAA CoastWatch (west)',
        'https://coastwatch.pfeg.noaa.gov/erddap',
        'NOAA_DHW',
        'Servidor usado pelo coleta_de_dados.py antigo.',
    ),
]

TIMEOUT = 25

# Onde o `copernicusmarine login` guarda as credenciais. Esse caminho e
# preferivel ao .env: fica fora do projeto, entao a senha nao corre risco de ir
# junto num commit nem de aparecer num print da pasta.
ARQUIVO_CREDENCIAIS_COPERNICUS = (
    Path.home() / '.copernicusmarine' / '.copernicusmarine-credentials'
)


def _origem_das_credenciais():
    """Diz de onde o Copernicus vai tirar as credenciais, sem le-las.

    Checar so o .env daria "sem credenciais" para quem fez `copernicusmarine
    login`, que e justamente o caminho recomendado.
    """
    if getattr(settings, 'COPERNICUSMARINE_SERVICE_USERNAME', ''):
        return '.env (COPERNICUSMARINE_SERVICE_USERNAME)'
    if ARQUIVO_CREDENCIAIS_COPERNICUS.exists():
        return str(ARQUIVO_CREDENCIAIS_COPERNICUS)
    return None


def _buscar(url):
    """Retorna (status, corpo) ou (None, motivo do erro)."""
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as resposta:
            return resposta.status, resposta.read().decode('utf-8', errors='replace')
    except urllib.error.HTTPError as exc:
        return exc.code, ''
    except Exception as exc:
        return None, f'{type(exc).__name__}: {exc}'


class Command(BaseCommand):
    help = 'Testa quais fontes externas respondem desta rede e o que publicam.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ssl',
            action='store_true',
            help='Diagnostica a verificacao de certificado de cada espelho.',
        )

    def handle(self, *args, **options):
        bundle = garantir_bundle_ca()
        if bundle:
            self.stdout.write(f'Bundle de CAs em uso: {bundle}')
        else:
            self.stdout.write(
                self.style.WARNING(
                    'Sem bundle de CAs proprio - usando a cadeia padrao do sistema.'
                )
            )
        self.stdout.write('')

        if options['ssl']:
            self._diagnosticar_ssl()
            return

        self.stdout.write('Testando espelhos do NOAA Coral Reef Watch...')
        self.stdout.write('')

        funcionando = []

        for nome, servidor, dataset, nota in CANDIDATOS_NOAA:
            url = f'{servidor}/griddap/{dataset}.das'
            status, corpo = _buscar(url)

            if status == 200:
                presentes = [v for v in VARIAVEIS_ERDDAP if v in corpo]
                ausentes = [v for v in VARIAVEIS_ERDDAP if v not in corpo]

                if not ausentes:
                    self.stdout.write(
                        self.style.SUCCESS(f'  [OK] {nome} - todas as 5 variaveis')
                    )
                    funcionando.append((nome, servidor, dataset, len(presentes)))
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  [PARCIAL] {nome} - tem {len(presentes)}/5. '
                            f'Faltam: {", ".join(ausentes)}'
                        )
                    )
                    if presentes:
                        funcionando.append((nome, servidor, dataset, len(presentes)))
            elif status is not None:
                self.stdout.write(
                    self.style.ERROR(f'  [HTTP {status}] {nome} - bloqueado ou id invalido')
                )
            else:
                self.stdout.write(self.style.ERROR(f'  [SEM ACESSO] {nome} - {corpo[:80]}'))

            self.stdout.write(f'           {servidor}')
            self.stdout.write(f'           dataset: {dataset} - {nota}')
            self.stdout.write('')

        self.stdout.write('Copernicus Marine...')
        status, corpo = _buscar('https://marine.copernicus.eu')
        if status == 200:
            origem = _origem_das_credenciais()
            if origem:
                self.stdout.write(
                    self.style.SUCCESS(f'  [OK] alcancavel, credenciais em {origem}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        '  [PARCIAL] alcancavel, mas sem credenciais.\n'
                        '            Rode "copernicusmarine login" e digite quando '
                        'ele pedir.\n'
                        '            Guarda em ~/.copernicusmarine, fora do projeto.'
                    )
                )
        else:
            self.stdout.write(self.style.ERROR(f'  [SEM ACESSO] {corpo[:80] or status}'))

        self.stdout.write('')
        self._recomendar(funcionando)

    def _diagnosticar_ssl(self):
        """Compara a cadeia de confianca do sistema com a do certifi.

        A diferenca entre as duas e o que separa "falta uma raiz nesta maquina"
        (conserto automatico) de "alguem esta no meio do caminho" (precisa da
        raiz da instituicao).
        """
        self.stdout.write('Diagnostico de certificado, espelho por espelho.')
        self.stdout.write('Pode demorar: cada host tem duas tentativas com timeout.')
        self.stdout.write('')

        estilos = {
            'ok': self.style.SUCCESS,
            'certifi': self.style.SUCCESS,
            'sistema': self.style.WARNING,
            'inalcancavel': self.style.WARNING,
            'interceptacao': self.style.ERROR,
        }

        for nome, servidor, _dataset, _nota in CANDIDATOS_NOAA:
            host = urllib.parse.urlparse(servidor).hostname
            self.stdout.write(f'{nome} ({host})')

            resultado = diagnosticar(host)
            veredito, explicacao = interpretar(resultado)

            self.stdout.write(
                f'  cadeia do sistema : {resultado["sistema"] or "verifica OK"}'
            )
            self.stdout.write(
                f'  bundle do certifi : {resultado["certifi"] or "verifica OK"}'
            )
            self.stdout.write(estilos[veredito](f'  -> {explicacao}'))

            if resultado['nomes_no_certificado']:
                self.stdout.write('  Nomes legiveis no certificado apresentado:')
                for texto in resultado['nomes_no_certificado']:
                    self.stdout.write(f'    {texto}')

            self.stdout.write('')

    def _recomendar(self, funcionando):
        atual_servidor = getattr(settings, 'NOAA_ERDDAP_SERVER', '')
        atual_dataset = getattr(settings, 'NOAA_ERDDAP_DATASET', '')
        self.stdout.write(f'Configuracao atual: {atual_servidor} + {atual_dataset}')

        # Servidor e dataset precisam vir do mesmo espelho. Trocar so um dos
        # dois no .env produz um 404 dificil de diagnosticar.
        pares_validos = {(s, d) for _, s, d, _ in CANDIDATOS_NOAA}
        if (atual_servidor, atual_dataset) not in pares_validos:
            esperado = next(
                (d for _, s, d, _ in CANDIDATOS_NOAA if s == atual_servidor), None
            )
            aviso = (
                'ATENCAO: servidor e dataset atuais nao formam um par conhecido. '
                'Cada espelho publica o produto sob um id proprio.'
            )
            if esperado:
                aviso += f'\n  Para {atual_servidor}, o dataset esperado e "{esperado}".'
            self.stdout.write(self.style.ERROR(aviso))

        self.stdout.write('')

        if not funcionando:
            self.stdout.write(
                self.style.ERROR(
                    'Nenhum espelho do NOAA respondeu desta rede. Tente de outra '
                    'conexao, ou use os CSVs ja baixados em backend/dados/.'
                )
            )
            return

        # Prefere o que publica mais variaveis; empate fica com a ordem da lista.
        melhor = max(funcionando, key=lambda item: item[3])
        nome, servidor, dataset, quantas = melhor

        if servidor == atual_servidor and dataset == atual_dataset:
            self.stdout.write(
                self.style.SUCCESS(
                    f'A configuracao atual ({nome}) e a melhor disponivel. '
                    'Pode rodar "manage.py ingerir".'
                )
            )
            return

        self.stdout.write(
            self.style.WARNING(
                f'Melhor opcao desta rede: {nome} ({quantas}/5 variaveis).\n'
                'Ajuste backend/.env com as DUAS linhas:\n\n'
                f'    NOAA_ERDDAP_SERVER={servidor}\n'
                f'    NOAA_ERDDAP_DATASET={dataset}\n'
            )
        )
