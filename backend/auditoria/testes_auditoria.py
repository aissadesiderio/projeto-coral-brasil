"""O que estes testes travam.

⚠️ **Um relatorio de auditoria errado e pior que nenhum**, porque a funcao dele
e ser confiado. Se ele diz "18.744 medicoes do CoralTemp entre 2020 e 2026" e o
numero sai de um agregado velho, o erro viaja para dentro de um artigo com
aparencia de verificado.

Os testes cobrem as tres formas de isso acontecer:

1. contar de agregado gravado em vez do dado (todos os testes de contagem
   escrevem no banco e conferem o numero que sai);
2. esconder o que falta (`lacunas`);
3. afirmar reprodutibilidade que nao existe (`codigo`).
"""

from datetime import date
from unittest import mock

from django.test import SimpleTestCase, TestCase

from aquaculture.models import (
    Checkpoint,
    Especie,
    ExecucaoIngestao,
    LocalRecife,
    MedicaoAmbiental,
)
from auditoria import codigo, procedencia


class CodigoTests(SimpleTestCase):
    def setUp(self):
        codigo.versao.cache_clear()

    def tearDown(self):
        codigo.versao.cache_clear()

    def test_no_repositorio_devolve_commit_e_ramo(self):
        atual = codigo.versao()
        self.assertIsNotNone(
            atual['commit'],
            'O proprio projeto e um repositorio git - se isto falha, '
            '`_git` parou de funcionar.',
        )
        self.assertEqual(len(atual['commit']), 40)
        self.assertEqual(atual['commit_curto'], atual['commit'][:12])
        self.assertIn(atual['sujo'], (True, False))

    def test_sem_git_declara_a_lacuna_em_vez_de_inventar(self):
        """🚨 Nao existe 'desconhecido' como valor.

        Devolver zeros ou a string 'desconhecido' fabricaria procedencia -
        exatamente o defeito do credito de imagem "Acervo local do projeto"
        (FONTES.md secao 2.1). Ausencia precisa continuar ausencia.
        """
        with mock.patch.object(codigo, '_git', return_value=None):
            codigo.versao.cache_clear()
            atual = codigo.versao()

        self.assertIsNone(atual['commit'])
        self.assertIsNone(atual['sujo'])
        self.assertIn('motivo', atual)

    def test_git_ausente_nao_levanta(self):
        """Metadado de procedencia nao pode derrubar o treino que ele descreve."""
        with mock.patch(
            'auditoria.codigo.subprocess.run', side_effect=OSError('sem git')
        ):
            codigo.versao.cache_clear()
            self.assertIsNone(codigo.versao()['commit'])

    def test_arvore_suja_nao_e_reproduzivel(self):
        with mock.patch.object(
            codigo, 'versao',
            return_value={'commit': 'a' * 40, 'sujo': True},
        ):
            self.assertFalse(codigo.reproduzivel())

    def test_arvore_limpa_e_reproduzivel(self):
        with mock.patch.object(
            codigo, 'versao',
            return_value={'commit': 'a' * 40, 'sujo': False},
        ):
            self.assertTrue(codigo.reproduzivel())

    def test_o_valor_e_coerente_dentro_da_execucao(self):
        """Dois artefatos da mesma corrida nao podem sair com hashes
        diferentes so porque alguem commitou no meio."""
        self.assertIs(codigo.versao(), codigo.versao())


class FontesTests(TestCase):
    def setUp(self):
        self.local = _local('abrolhos-ba')
        MedicaoAmbiental.objects.all().delete()

    def test_conta_do_dado_e_separa_por_dataset(self):
        """🚨 A separacao por dataset nao e detalhe.

        O Copernicus emenda reanalise e analise na mesma serie. Agrupar so por
        fonte apagaria a costura, que e justamente o que precisa ser citavel.
        """
        _medicao(self.local, date(2020, 1, 1), fonte='copernicus', dataset='reanalise')
        _medicao(self.local, date(2020, 1, 2), fonte='copernicus', dataset='reanalise')
        _medicao(self.local, date(2026, 1, 1), fonte='copernicus', dataset='analise')

        retrato = {
            item['dataset_id']: item for item in procedencia.fontes()
        }
        self.assertEqual(retrato['reanalise']['medicoes'], 2)
        self.assertEqual(retrato['analise']['medicoes'], 1)
        self.assertEqual(retrato['reanalise']['periodo']['inicio'], '2020-01-01')
        self.assertEqual(retrato['reanalise']['periodo']['fim'], '2020-01-02')

    def test_separa_por_flag_de_qualidade(self):
        _medicao(self.local, date(2020, 1, 1))
        _medicao(self.local, date(2020, 1, 2), variavel='dhw', flag='degradado')

        item = procedencia.fontes()[0]
        self.assertEqual(item['por_qualidade'], {'degradado': 1, 'ok': 1})


class LocaisTests(TestCase):
    def test_local_sem_serie_aparece(self):
        """⚠️ Listar so quem tem dado responde "o que temos" e esconde "o que
        falta" - e o que falta e metade da auditoria."""
        _local('sem-dado-xx', latitude=None, longitude=None)
        slugs = {item['slug'] for item in procedencia.locais()}
        self.assertIn('sem-dado-xx', slugs)

        item = next(i for i in procedencia.locais() if i['slug'] == 'sem-dado-xx')
        self.assertEqual(item['medicoes'], 0)
        self.assertFalse(item['tem_coordenadas'])


class LacunasTests(TestCase):
    def setUp(self):
        MedicaoAmbiental.objects.all().delete()
        Checkpoint.objects.all().delete()
        ExecucaoIngestao.objects.all().delete()

    def _tipos(self):
        return {item['tipo'] for item in procedencia.lacunas()}

    def test_local_sem_coordenada_vira_lacuna(self):
        _local('sem-coord-xx', latitude=None, longitude=None)
        self.assertIn('local_sem_coordenada', self._tipos())

    def test_especie_sem_ano_de_avaliacao_vira_lacuna(self):
        Especie.objects.create(
            nome_cientifico='Testus exemplaris', nome_comum='Teste',
            iucn_categoria='VU',
        )
        lacuna = next(
            item for item in procedencia.lacunas()
            if item['tipo'] == 'especie_sem_procedencia_iucn'
        )
        self.assertIn('Testus exemplaris', lacuna['quais'])

    def test_checkpoint_esgotado_vira_lacuna(self):
        Checkpoint.objects.create(
            tarefa='ingestao.x.y', unidade='bloco', status=Checkpoint.FALHOU,
            tentativas=5,
        )
        self.assertIn('checkpoint_esgotado', self._tipos())

    def test_ingestao_que_falhou_vira_lacuna(self):
        ExecucaoIngestao.objects.create(fonte='noaa_crw', status='falha')
        self.assertIn('ingestao_falhou', self._tipos())

    def test_arvore_suja_vira_lacuna(self):
        with mock.patch.object(codigo, 'reproduzivel', return_value=False):
            self.assertIn('codigo_nao_reproduzivel', self._tipos())

    def test_arvore_limpa_nao_vira_lacuna(self):
        with mock.patch.object(codigo, 'reproduzivel', return_value=True):
            self.assertNotIn('codigo_nao_reproduzivel', self._tipos())

    def test_toda_lacuna_diz_a_consequencia(self):
        """🚨 Uma lacuna sem consequencia declarada e uma contagem, nao um aviso.

        Quem le precisa saber o que **deixa de poder afirmar** - senao o
        relatorio vira uma lista de numeros que ninguem sabe interpretar, e a
        reacao natural e ignorar.
        """
        _local('sem-coord-xx', latitude=None, longitude=None)
        ExecucaoIngestao.objects.create(fonte='noaa_crw', status='falha')

        for item in procedencia.lacunas():
            self.assertTrue(
                item.get('consequencia'),
                f'A lacuna {item["tipo"]!r} nao diz o que ela impede afirmar.',
            )


class MontarTests(TestCase):
    def test_resumo_soma_as_fontes(self):
        local = _local('abrolhos-ba')
        MedicaoAmbiental.objects.all().delete()
        _medicao(local, date(2020, 1, 1))
        _medicao(local, date(2020, 1, 2))

        retrato = procedencia.montar(incluir_modelos=False)
        self.assertEqual(retrato['resumo']['medicoes'], 2)
        self.assertEqual(retrato['versao_formato'], 1)
        self.assertIn('codigo', retrato)
        self.assertNotIn('modelos', retrato)

    def test_serializa_em_json(self):
        """O retrato vira anexo de resultado - se nao serializa, nao serve."""
        import json
        retrato = procedencia.montar(incluir_modelos=False)
        self.assertIn('gerado_em', json.loads(json.dumps(retrato, default=str)))


def _local(slug, latitude=-17.972, longitude=-38.688):
    local, _ = LocalRecife.objects.get_or_create(
        slug=slug,
        defaults={
            'nome': slug, 'estado': 'BA', 'cidade': 'Caravelas',
            'latitude': latitude, 'longitude': longitude, 'ativo': True,
        },
    )
    return local


def _medicao(local, dia, fonte='noaa_crw', dataset='dhw_5km', variavel='sst',
             flag='ok'):
    return MedicaoAmbiental.objects.create(
        local_recife=local, data=dia, variavel=variavel, valor=27.0,
        unidade='degree_C', fonte=fonte, dataset_id=dataset, quality_flag=flag,
    )
