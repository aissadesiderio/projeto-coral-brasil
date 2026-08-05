"""As constraints estao declaradas — estes testes verificam que o banco as aplica.

🚨 **A distancia entre as duas coisas e o motivo deste arquivo existir.** Ate
28/07/2026 o projeto tinha `UniqueConstraint` no modelo e **nenhum teste**
conferindo que uma duplicata e recusada. Declarar e aplicar sao eventos
diferentes: a constraint pode nao ter migrado, pode ter sido criada com nome
divergente, ou pode ter sido removida por uma migracao posterior — e nada disso
aparece ate a primeira duplicata chegar, provavelmente numa reingestao.

O item de go-live pedia a camada de persistencia **validada**. Isto e o que a
palavra significa.

⚠️ Estes testes rodam contra o PostgreSQL de teste, e nao contra um SQLite em
memoria: a constraint precisa ser verificada no banco que vai para produção.
"""

from datetime import date

from django.db import IntegrityError, transaction
from django.test import TestCase

from aquaculture.models import (
    DatasetCatalogo,
    Especie,
    LocalRecife,
    MedicaoAmbiental,
)


class BaseComLocal(TestCase):
    def setUp(self):
        MedicaoAmbiental.objects.all().delete()
        LocalRecife.objects.all().delete()

        self.local = LocalRecife.objects.create(
            slug='teste-abrolhos', nome='Abrolhos', estado='BA',
            cidade='Caravelas', latitude=-17.9, longitude=-38.6,
        )

    def medicao(self, **extras):
        campos = {
            'local_recife': self.local,
            'data': date(2026, 7, 24),
            'variavel': 'sst',
            'valor': 25.0,
            'unidade': '°C',
            'fonte': 'noaa_crw',
            'dataset_id': 'dhw_5km',
        }
        campos.update(extras)
        return MedicaoAmbiental.objects.create(**campos)


class MedicaoAmbientalConstraintTests(BaseComLocal):
    def test_duplicata_exata_e_recusada_pelo_banco(self):
        """🚨 A garantia central da idempotencia da ingestao.

        Sem ela, rodar `ingerir` duas vezes no mesmo periodo dobraria a serie
        em silencio — e o modelo treinaria com cada dia contado duas vezes.
        """
        self.medicao()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.medicao()

    def test_a_mesma_variavel_de_outra_fonte_e_permitida(self):
        """E deliberado, e nao brecha.

        SST existe no CRW e no Copernicus. A chave inclui `fonte` justamente
        para que as duas possam coexistir — a escolha entre elas e feita na
        leitura, e nao apagando uma na escrita. Se esta linha passar a falhar,
        a proveniencia por valor deixou de ser possivel.
        """
        self.medicao()
        self.medicao(fonte='copernicus', dataset_id='cmems_phy')

        self.assertEqual(MedicaoAmbiental.objects.count(), 2)

    def test_variaveis_diferentes_no_mesmo_dia_convivem(self):
        self.medicao(variavel='sst')
        self.medicao(variavel='dhw', unidade='°C·semana')

        self.assertEqual(MedicaoAmbiental.objects.count(), 2)

    def test_datas_diferentes_convivem(self):
        self.medicao(data=date(2026, 7, 24))
        self.medicao(data=date(2026, 7, 25))

        self.assertEqual(MedicaoAmbiental.objects.count(), 2)

    def test_locais_diferentes_convivem(self):
        outro = LocalRecife.objects.create(
            slug='teste-picao', nome='Picao', estado='PB', cidade='JP',
            latitude=-7.1, longitude=-34.8,
        )
        self.medicao()
        self.medicao(local_recife=outro)

        self.assertEqual(MedicaoAmbiental.objects.count(), 2)

    def test_valor_nulo_nao_escapa_da_constraint(self):
        """Reprovado na validacao fisica continua sendo uma linha unica.

        Em SQL, `NULL != NULL` — mas o nulo aqui esta em `valor`, que **nao**
        faz parte da chave. Se um dia entrar, duplicatas passariam a ser
        aceitas silenciosamente.
        """
        self.medicao(valor=None, quality_flag='invalido')

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.medicao(valor=None, quality_flag='invalido')


class IdentificadorUnicoTests(BaseComLocal):
    def test_slug_de_local_e_unico(self):
        """O slug e a chave publica: rota da API, id no grafo, filtro."""
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                LocalRecife.objects.create(
                    slug='teste-abrolhos', nome='Outro', estado='BA',
                    cidade='X', latitude=-1.0, longitude=-1.0,
                )

    def test_nome_cientifico_de_especie_e_unico(self):
        Especie.objects.filter(nome_cientifico='Testus testus').delete()
        Especie.objects.create(
            nome_comum='Coral de teste', nome_cientifico='Testus testus',
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Especie.objects.create(
                    nome_comum='Outro nome', nome_cientifico='Testus testus',
                )

    def test_id_de_dataset_e_unico(self):
        DatasetCatalogo.objects.filter(pk='teste-unico').delete()
        DatasetCatalogo.objects.create(
            id='teste-unico', titulo='A', fonte='X', tipo_dado='Y',
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                DatasetCatalogo.objects.create(
                    id='teste-unico', titulo='B', fonte='X', tipo_dado='Y',
                )


class IndicesDeclaradosTests(BaseComLocal):
    """Os indices que sustentam as consultas quentes existem.

    Nao medem desempenho — medicao fica no `conferir_persistencia`, contra o
    banco real e com volume real. Aqui a pergunta e mais basica: **o indice
    chegou a ser criado?** Uma migracao perdida some com ele sem barulho, e o
    efeito so aparece quando a tabela cresce.
    """

    ESPERADOS = (
        ('local_recife_id', 'data', 'variavel', 'fonte'),  # a unicidade
        ('variavel', 'data'),
        ('local_recife_id', 'data'),
    )

    def indices_da_tabela(self):
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT indexdef FROM pg_indexes "
                "WHERE tablename = 'aquaculture_medicaoambiental'"
            )
            return [linha[0] for linha in cursor.fetchall()]

    def test_os_indices_das_consultas_quentes_existem(self):
        from django.db import connection

        if connection.vendor != 'postgresql':
            self.skipTest('Leitura de indices especifica do PostgreSQL.')

        definicoes = self.indices_da_tabela()

        for colunas in self.ESPERADOS:
            achou = any(
                all(c in definicao for c in colunas)
                for definicao in definicoes
            )
            self.assertTrue(
                achou,
                f'Nenhum indice cobre {colunas}. Indices presentes: {definicoes}',
            )
