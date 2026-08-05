"""Lista as especies cuja categoria de conservacao ninguem consegue citar.

🚨 **Existe porque conferencia manual nao escala como memoria, mas escala como
relatorio.** Com 9 especies alguem lembra; se as ocorrencias passarem a vir do
OBIS/GBIF pela bbox do recife, o catalogo vai para centenas — **cada uma
chegando sem procedencia nenhuma**. O que quebra nao e a conferencia em si: e
depender de alguem se lembrar de que ela existe.

⚠️ **Ele nao busca nada na internet, e isso e deliberado.** A API da IUCN exige
token, e o pedido deste projeto foi **recusado em 31/07/2026**. O comando faz o
que da para fazer sem ela: diz **o que falta** e **onde conferir**, montando o
link da ficha quando ha `iucn_taxon_id`. Preencher continua sendo ato humano —
e o `iucn_origem` grava por qual via foi.

Duas condicoes diferentes, e a distincao importa:

| | O que significa |
|---|---|
| **sem procedencia** | falta categoria ou falta o ano. O site nao exibe nada |
| **conferencia vencida** | ha categoria e ano, mas ninguem confere ha muito tempo |

A segunda e a que pegaria o defeito real: `Mussismilia braziliensis` estava
gravada como VU e a IUCN a registra como CR desde 2022-2. Nada mudou no
registro local — foi a IUCN que publicou outra avaliacao.
"""

from django.core.management.base import BaseCommand

from aquaculture.models import Especie

BUSCA_IUCN = 'https://www.iucnredlist.org/search?query={nome}&searchType=species'


class Command(BaseCommand):
    help = (
        'Lista as especies sem procedencia de conservacao, ou com a '
        'conferencia vencida, com o link para conferir.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--vencidas', action='store_true',
            help='So as que tem procedencia mas nao sao conferidas ha tempo.',
        )
        parser.add_argument(
            '--todas', action='store_true',
            help='Inclui tambem as que estao em dia, para conferir o acervo.',
        )

    def handle(self, *args, **opcoes):
        especies = list(Especie.objects.order_by('nome_cientifico'))
        if not especies:
            self.stdout.write('Nenhuma especie cadastrada.')
            return

        sem_procedencia = [e for e in especies if not e.iucn_tem_procedencia]
        vencidas = [e for e in especies if e.iucn_conferencia_vencida]

        if opcoes['todas']:
            self._secao('Todas as especies', especies)
        elif opcoes['vencidas']:
            self._secao('Conferencia vencida', vencidas)
        else:
            self._secao('Sem procedencia — o site nao exibe categoria', sem_procedencia)
            self._secao('Conferencia vencida', vencidas)

        self._resumo(especies, sem_procedencia, vencidas)

    def _secao(self, titulo, especies):
        if not especies:
            return

        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING(f'{titulo} ({len(especies)})'))
        for especie in especies:
            self.stdout.write(f'  {especie.nome_cientifico}')
            self.stdout.write(f'    categoria : {self._categoria(especie)}')
            self.stdout.write(f'    conferir  : {self._onde_conferir(especie)}')

    def _categoria(self, especie):
        if not especie.iucn_categoria:
            return '(nenhuma registrada)'

        partes = [f'{especie.get_iucn_categoria_display()} ({especie.iucn_categoria})']
        if especie.iucn_avaliado_em:
            partes.append(f'avaliada em {especie.iucn_avaliado_em}')
        else:
            partes.append('SEM ANO')
        if especie.iucn_versao:
            partes.append(f'versao {especie.iucn_versao}')
        if especie.iucn_consultado_em:
            partes.append(f'conferida em {especie.iucn_consultado_em}')
        else:
            partes.append('nunca conferida')
        if especie.iucn_origem:
            partes.append(f'via {especie.get_iucn_origem_display()}')
        return ' — '.join(partes)

    def _onde_conferir(self, especie):
        """O link direto quando ha id; a busca quando nao ha.

        ⚠️ A busca **nao** e o mesmo que a ficha: ela pode devolver varios
        resultados, e escolher o errado e o defeito de sinonimo em outra forma.
        Por isso o `iucn_taxon_id` vale a pena — ele fixa qual ficha.
        """
        if especie.iucn_taxon_id:
            return f'https://www.iucnredlist.org/species/{especie.iucn_taxon_id}'
        if especie.fonte_iucn_url:
            return especie.fonte_iucn_url
        return BUSCA_IUCN.format(nome=especie.nome_cientifico.replace(' ', '%20'))

    def _resumo(self, especies, sem_procedencia, vencidas):
        self.stdout.write('')
        self.stdout.write(
            f'  {len(especies)} especie(s): '
            f'{len(especies) - len(sem_procedencia)} exibiveis, '
            f'{len(sem_procedencia)} sem procedencia, '
            f'{len(vencidas)} com conferencia vencida.'
        )

        if not sem_procedencia and not vencidas:
            self.stdout.write(self.style.SUCCESS(
                '  Todas as categorias podem ser exibidas e citadas.'
            ))
            return

        self.stdout.write('')
        self.stdout.write(
            '  Para preencher: painel administrativo, secao "Conservacao '
            '(IUCN)".\n'
            '  O ANO da avaliacao e obrigatorio — sem ele o site nao exibe a\n'
            '  categoria, de proposito. E registre "Como foi obtida": um valor\n'
            '  vindo do Wikidata ou do GBIF e legitimo, mas cita-se o terceiro,\n'
            '  nao a IUCN.'
        )
