"""Testes do endpoint da serie ambiental.

O que protegem, em ordem de gravidade:

1. **A paginacao existe e tem teto.** Sao 57.420 linhas crescendo 24/dia; sem
   paginacao a resposta seria a serie inteira, e sem teto o cliente desfaria a
   paginacao com `?page_size=999999`.
2. **A proveniencia vai no payload.** Servir o numero sem dizer de onde veio
   entregaria exatamente o que este projeto existe para nao fazer.
3. **Valor nulo sai como nulo, nunca como zero.** O pipeline legado gravava pH 0
   e salinidade 0 — fisicamente impossiveis — ao preencher lacuna.
4. **Data invalida falha alto.** Sem isso, `?de=ontem` seria ignorado e o
   cliente receberia tudo achando que recebeu o recorte que pediu.
"""

from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from aquaculture.models import LocalRecife, MedicaoAmbiental

SENHA_FORTE = 'uma-senha-bem-forte-2026'


@override_settings(OFFLINE_MODE=False)
class MedicaoAmbientalApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        MedicaoAmbiental.objects.all().delete()
        LocalRecife.objects.all().delete()

        cls.abrolhos = LocalRecife.objects.create(
            slug='teste-abrolhos', nome='Abrolhos', estado='BA',
            cidade='Caravelas', latitude=-17.9, longitude=-38.6,
        )
        cls.picao = LocalRecife.objects.create(
            slug='teste-picao', nome='Picaozinho', estado='PB',
            cidade='Joao Pessoa', latitude=-7.1, longitude=-34.8,
        )

        MedicaoAmbiental.objects.create(
            local_recife=cls.abrolhos, data=date(2026, 7, 24), variavel='sst',
            valor=25.0, unidade='°C', fonte='noaa_crw', dataset_id='dhw_5km',
        )
        MedicaoAmbiental.objects.create(
            local_recife=cls.abrolhos, data=date(2026, 7, 24), variavel='dhw',
            valor=0.0, unidade='°C·semana', fonte='noaa_crw',
            dataset_id='dhw_5km',
        )
        MedicaoAmbiental.objects.create(
            local_recife=cls.abrolhos, data=date(2026, 7, 20),
            variavel='salinidade', valor=37.4, unidade='PSU',
            fonte='copernicus', dataset_id='cmems_phy_my',
        )
        MedicaoAmbiental.objects.create(
            local_recife=cls.picao, data=date(2026, 7, 24), variavel='sst',
            valor=28.0, unidade='°C', fonte='noaa_crw', dataset_id='dhw_5km',
        )
        # A que foi reprovada na validacao fisica.
        cls.reprovada = MedicaoAmbiental.objects.create(
            local_recife=cls.picao, data=date(2026, 7, 23), variavel='ph',
            valor=None, unidade='', fonte='copernicus',
            dataset_id='cmems_bgc_car', quality_flag='invalido',
            observacao='pH 2,5 fora da faixa fisica do oceano',
        )

    def buscar(self, consulta=''):
        return self.client.get(reverse('medicao_list') + consulta)

    # --- paginacao ----------------------------------------------------------

    def test_a_resposta_vem_paginada(self):
        corpo = self.buscar().json()

        for campo in ('count', 'total_paginas', 'page_size', 'results'):
            self.assertIn(campo, corpo)
        self.assertEqual(corpo['count'], 5)

    def test_page_size_e_respeitado(self):
        corpo = self.buscar('?page_size=2').json()

        self.assertEqual(len(corpo['results']), 2)
        self.assertEqual(corpo['count'], 5)
        self.assertEqual(corpo['total_paginas'], 3)
        self.assertIsNotNone(corpo['next'])

    @override_settings(DRF_MAX_PAGE_SIZE=3)
    def test_o_teto_impede_o_cliente_de_desfazer_a_paginacao(self):
        """🚨 Sem teto, `?page_size=999999` devolve a serie inteira."""
        corpo = self.buscar('?page_size=999999').json()

        self.assertEqual(corpo['page_size'], 3)
        self.assertEqual(len(corpo['results']), 3)

    def test_paginar_nao_repete_nem_pula_linha(self):
        """Ordem nao determinista faz linhas trocarem de pagina entre requisicoes."""
        primeira = self.buscar('?page_size=2').json()['results']
        segunda = self.buscar('?page_size=2&page=2').json()['results']
        terceira = self.buscar('?page_size=2&page=3').json()['results']

        ids = [x['id'] for x in primeira + segunda + terceira]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(ids), 5)

    # --- proveniencia -------------------------------------------------------

    def test_a_proveniencia_vem_no_payload(self):
        """Nao e opcional nem fica atras de parametro."""
        item = self.buscar('?local=teste-abrolhos&variavel=sst').json()['results'][0]

        self.assertEqual(item['fonte'], 'noaa_crw')
        self.assertEqual(item['dataset_id'], 'dhw_5km')
        self.assertEqual(item['quality_flag'], 'ok')
        self.assertIn('observacao', item)

    def test_o_local_sai_como_slug(self):
        item = self.buscar('?local=teste-picao&variavel=sst').json()['results'][0]

        self.assertEqual(item['local'], 'teste-picao')

    # --- nulo -------------------------------------------------------------

    def test_valor_reprovado_sai_nulo_e_nao_zero(self):
        """🚨 O defeito do pipeline legado: `.fillna(0)` gravava pH 0."""
        corpo = self.buscar('?qualidade=invalido').json()

        self.assertEqual(corpo['count'], 1)
        item = corpo['results'][0]
        self.assertIsNone(item['valor'])
        self.assertNotEqual(item['valor'], 0)

    def test_o_motivo_da_reprovacao_acompanha_o_nulo(self):
        """Nulo sem motivo e lacuna muda; com motivo, e informacao."""
        item = self.buscar('?qualidade=invalido').json()['results'][0]

        self.assertIn('fora da faixa', item['observacao'])

    def test_zero_legitimo_continua_zero(self):
        """DHW 0 quer dizer "sem estresse", e nao "sem dado"."""
        item = self.buscar('?variavel=dhw').json()['results'][0]

        self.assertEqual(item['valor'], 0.0)
        self.assertIsNotNone(item['valor'])

    # --- filtros ------------------------------------------------------------

    def test_filtra_por_local(self):
        self.assertEqual(self.buscar('?local=teste-picao').json()['count'], 2)

    def test_filtra_por_variavel(self):
        self.assertEqual(self.buscar('?variavel=sst').json()['count'], 2)

    def test_variavel_pode_repetir(self):
        corpo = self.buscar('?variavel=sst&variavel=dhw').json()

        self.assertEqual(corpo['count'], 3)

    def test_variavel_nao_usada_pelo_modelo_continua_pesquisavel_e_baixavel(self):
        """🚨 Decisao de produto: o catalogo para download nunca fica restrito
        as quatro variaveis que `ml/dataset.py::VARIAVEIS_BASELINE` usa para
        prever. `ph` nao entra no modelo (e nem tem dado real hoje fora dos
        testes — ver docs/FONTES.md secao 6), mas se um dia tiver, este
        endpoint precisa continuar servindo-o do mesmo jeito que serve
        `sst`/`dhw`/`salinidade`/`oxigenio`. Local: nunca em `get_queryset`."""
        corpo = self.buscar('?variavel=ph').json()

        self.assertEqual(corpo['count'], 1)
        self.assertEqual(corpo['results'][0]['variavel'], 'ph')

    def test_filtra_por_fonte(self):
        self.assertEqual(self.buscar('?fonte=copernicus').json()['count'], 2)

    def test_filtra_por_periodo(self):
        corpo = self.buscar('?de=2026-07-24&ate=2026-07-24').json()

        self.assertEqual(corpo['count'], 3)

    def test_o_periodo_e_inclusivo_nas_duas_pontas(self):
        self.assertEqual(self.buscar('?de=2026-07-20&ate=2026-07-20').json()['count'], 1)

    def test_os_filtros_se_combinam(self):
        corpo = self.buscar(
            '?local=teste-abrolhos&fonte=noaa_crw&de=2026-07-24'
        ).json()

        self.assertEqual(corpo['count'], 2)

    def test_sem_filtro_devolve_tudo(self):
        self.assertEqual(self.buscar().json()['count'], 5)

    def test_filtro_que_nao_casa_devolve_lista_vazia_e_nao_erro(self):
        corpo = self.buscar('?local=nao-existe').json()

        self.assertEqual(corpo['count'], 0)
        self.assertEqual(corpo['results'], [])

    # --- entrada invalida ---------------------------------------------------

    def test_data_invalida_falha_alto(self):
        """🚨 Sem isto o filtro seria ignorado e o cliente receberia TUDO."""
        resposta = self.buscar('?de=ontem')

        self.assertEqual(resposta.status_code, 400)
        self.assertIn('AAAA-MM-DD', resposta.json()['detail'])

    def test_data_invalida_no_ate_tambem_falha(self):
        self.assertEqual(self.buscar('?ate=32/13/2026').status_code, 400)

    # --- ordenacao ----------------------------------------------------------

    def test_vem_do_mais_recente_para_o_mais_antigo(self):
        datas = [x['data'] for x in self.buscar().json()['results']]

        self.assertEqual(datas, sorted(datas, reverse=True))

    # --- modo offline -------------------------------------------------------

    @override_settings(OFFLINE_MODE=True)
    def test_respeita_o_modo_offline(self):
        resposta = self.buscar()

        self.assertEqual(resposta.status_code, 503)


@override_settings(OFFLINE_MODE=False)
class DownloadCsvTests(MedicaoAmbientalApiTests):
    """`?formato=csv` — o download que faz o site ser citavel.

    Herda o mesmo cenario da suite acima de proposito: o CSV precisa responder
    aos **mesmos filtros** que o JSON, e testa-lo sobre outros dados esconderia
    justamente a divergencia que importa.

    🚨 **Todo teste aqui roda logado como conta aprovada.** Ate a
    funcionalidade de contas, baixar o CSV era anonimo — agora exige conta
    aprovada (ver `GateDoDownloadTests` para quem **nao** e). O `setUp` faz
    isso uma vez para a classe inteira, para os testes que ja existiam
    continuarem exercitando exatamente o que exerciam antes: forma do CSV,
    filtros, nulo, nome do arquivo — nao a permissao, que tem suite propria.
    """

    def setUp(self):
        usuario = User.objects.create_user(username='baixador', password=SENHA_FORTE)
        usuario.perfil.aprovado = True
        usuario.perfil.save()
        self.client.login(username='baixador', password=SENHA_FORTE)

    def baixar(self, consulta=''):
        resposta = self.buscar(f'?formato=csv{consulta}')
        corpo = b''.join(resposta.streaming_content).decode('utf-8')
        return resposta, [linha for linha in corpo.splitlines() if linha]

    def celulas(self, consulta=''):
        import csv

        _, linhas = self.baixar(consulta)
        return list(csv.reader(linhas))

    def test_sai_como_csv_para_download(self):
        resposta, linhas = self.baixar()

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta['Content-Type'], 'text/csv')
        self.assertIn('attachment', resposta['Content-Disposition'])
        self.assertEqual(len(linhas), 6)   # cabecalho + as 5 medicoes

    def test_a_proveniencia_vem_junto(self):
        """Sem `fonte` e `quality_flag` o arquivo baixado vira planilha qualquer."""
        cabecalho = self.celulas()[0]

        self.assertEqual(
            cabecalho,
            ['local', 'data', 'variavel', 'valor', 'unidade',
             'fonte', 'dataset_id', 'quality_flag', 'observacao'],
        )

    def test_valor_nulo_sai_vazio_e_nunca_como_zero(self):
        """🚨 Zero e leitura valida; "reprovado na validacao" nao e zero.

        Este e o defeito do pipeline legado (pH 0, salinidade 0) reaparecendo
        em formato de arquivo — e num CSV o leitor abre no Excel sem nenhum
        aviso por perto.
        """
        linhas = self.celulas('&qualidade=invalido')
        cabecalho, registro = linhas[0], linhas[1]
        campos = dict(zip(cabecalho, registro))

        self.assertEqual(campos['valor'], '')
        self.assertNotEqual(campos['valor'], '0')
        self.assertEqual(campos['quality_flag'], 'invalido')
        self.assertIn('fora da faixa fisica', campos['observacao'])

    def test_o_zero_de_verdade_continua_sendo_zero(self):
        """O contraponto do teste acima: nem toda celula vazia e nulo."""
        linhas = self.celulas('&variavel=dhw')
        campos = dict(zip(linhas[0], linhas[1]))

        self.assertEqual(float(campos['valor']), 0.0)

    def test_responde_aos_mesmos_filtros_que_o_json(self):
        for consulta, esperado in (
            ('&local=teste-picao', 2),
            ('&variavel=sst', 2),
            ('&fonte=copernicus', 2),
            ('&de=2026-07-24', 3),
            ('&local=teste-abrolhos&variavel=sst', 1),
        ):
            with self.subTest(consulta=consulta):
                _, linhas = self.baixar(consulta)

                self.assertEqual(len(linhas) - 1, esperado)

    def test_o_download_nao_e_paginado(self):
        """⚠️ Paginar o download obrigaria a costurar o arquivo de volta.

        E a primeira pagina passaria por "os dados" com facilidade demais.
        """
        _, linhas = self.baixar('&page_size=2')

        self.assertEqual(len(linhas) - 1, 5)

    def test_o_nome_do_arquivo_descreve_o_recorte(self):
        """Tres `medicoes.csv` na pasta de downloads sao indistinguiveis."""
        resposta, _ = self.baixar('&local=teste-picao&variavel=sst')

        self.assertIn(
            'filename="medicoes-teste-picao-sst.csv"',
            resposta['Content-Disposition'],
        )

    def test_sem_filtro_o_nome_e_generico(self):
        resposta, _ = self.baixar()

        self.assertIn('filename="medicoes.csv"', resposta['Content-Disposition'])

    def test_data_invalida_falha_alto_tambem_no_csv(self):
        """🚨 O caminho do CSV nao pode escapar da validacao do JSON.

        Aqui o estrago seria maior: um arquivo baixado sobrevive a sessao, e
        ninguem confere depois se o recorte pedido foi o recorte aplicado.
        """
        resposta = self.buscar('?formato=csv&de=ontem')

        self.assertEqual(resposta.status_code, 400)

    @override_settings(OFFLINE_MODE=True)
    def test_o_csv_tambem_respeita_o_modo_offline(self):
        self.assertEqual(self.buscar('?formato=csv').status_code, 503)


@override_settings(OFFLINE_MODE=False)
class GateDoDownloadTests(MedicaoAmbientalApiTests):
    """Quem pode baixar o CSV, e o que continua igual para quem so le.

    🚨 O bloqueio mora **so** dentro do ramo `formato=csv` de `list()` — este
    teste e o que prova que o JSON (o que alimenta o grafico publico de cada
    recife) nunca foi tocado.
    """

    def test_anonimo_nao_baixa(self):
        resposta = self.buscar('?formato=csv')

        self.assertEqual(resposta.status_code, 401)

    def test_autenticado_sem_aprovacao_nao_baixa(self):
        usuario = User.objects.create_user(username='pendente', password=SENHA_FORTE)
        self.assertFalse(usuario.perfil.aprovado)
        self.client.login(username='pendente', password=SENHA_FORTE)

        resposta = self.buscar('?formato=csv')

        self.assertEqual(resposta.status_code, 403)

    def test_aprovado_baixa(self):
        usuario = User.objects.create_user(username='aprovado', password=SENHA_FORTE)
        usuario.perfil.aprovado = True
        usuario.perfil.save()
        self.client.login(username='aprovado', password=SENHA_FORTE)

        self.assertEqual(self.buscar('?formato=csv').status_code, 200)

    def test_master_baixa_sem_precisar_de_perfil_aprovado(self):
        master = User.objects.create_superuser(
            username='master', email='m@example.com', password=SENHA_FORTE,
        )
        self.assertFalse(master.perfil.aprovado)
        self.client.login(username='master', password=SENHA_FORTE)

        self.assertEqual(self.buscar('?formato=csv').status_code, 200)

    def test_json_continua_publico_para_quem_nao_esta_logado(self):
        """🚨 A regressao que mais importa: ninguem precisa de conta so para
        ver a serie no grafico do site."""
        resposta = self.buscar()

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()['count'], 5)
