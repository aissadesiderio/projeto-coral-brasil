"""O que o site diz ter de cada local — e de quem e a foto dele.

Dois defeitos medidos em 12/08/2026, os dois da mesma familia: **o projeto
guardava e nao mostrava**.

1. Oito variaveis ingeridas por recife, duas exibidas. As outras seis — ~7.200
   medicoes de cada, desde 2020 — nao apareciam em numero nenhum do site.
2. `profundidade_media_m` e a area no modelo desde a migracao `0014`, nunca num
   serializer. Nenhuma previsao usa esses campos, e foi exatamente por isso que
   a ausencia nao quebrou nada por um mes. O campo de area virou **dois** em
   13/08/2026 (migracao `0031`), com uma fonte para cada — ver
   `AreasSemeadasTests`.

E um terceiro, de outra familia: a foto do local nao tinha **onde** registrar
autor, fonte ou local de captura (migracao `0030`). Ver docs/FONTES.md §2.2.
"""

from datetime import date

from django.test import TestCase, override_settings
from django.urls import reverse

from . import acervo
from .code_sync import build_sync_payload
from .models import LocalRecife, MedicaoAmbiental


def _medicao(local, variavel, dia, fonte='noaa_crw', valor=1.0, unidade='x'):
    return MedicaoAmbiental.objects.create(
        local_recife=local, data=dia, variavel=variavel, valor=valor,
        unidade=unidade, fonte=fonte,
    )


class AcervoDoLocalTests(TestCase):
    """`acervo.para_local` — uma linha por variavel que **tem** medicao."""

    def setUp(self):
        self.local = LocalRecife.objects.create(
            slug='acervo-ba', nome='Acervo', estado='Bahia', cidade='Caravelas',
            latitude=-17.9, longitude=-38.6,
        )
        self.outro = LocalRecife.objects.create(
            slug='outro-pe', nome='Outro', estado='Pernambuco', cidade='Ipojuca',
            latitude=-8.5, longitude=-34.9,
        )

        _medicao(self.local, 'sst', date(2020, 1, 1), unidade='°C')
        _medicao(self.local, 'sst', date(2026, 7, 24), unidade='°C')
        _medicao(self.local, 'dhw', date(2026, 7, 24), unidade='°C·semana')
        _medicao(self.local, 'baa', date(2026, 7, 24), unidade='0-5')
        _medicao(self.local, 'hotspot', date(2026, 7, 24), unidade='°C')
        _medicao(self.local, 'salinidade', date(2026, 7, 24),
                 fonte='copernicus', unidade='PSU')
        _medicao(self.outro, 'oxigenio', date(2026, 7, 24),
                 fonte='copernicus', unidade='mmol/m³')

    def test_lista_todas_as_variaveis_medidas_e_nao_so_as_do_grafico(self):
        """🚨 O defeito em uma linha: o grafico mostra `sst` e `dhw`, e o site
        nao dizia que as outras quatro existiam."""
        variaveis = {linha['variavel'] for linha in acervo.para_local('acervo-ba')}

        self.assertEqual(
            variaveis, {'sst', 'dhw', 'baa', 'hotspot', 'salinidade'},
        )

    def test_nao_lista_variavel_sem_medicao_neste_local(self):
        """Uma linha "oxigenio — 0 medicoes" seria lida como lacuna **deste**
        recife. O oxigenio existe no projeto; so nao neste local."""
        variaveis = {linha['variavel'] for linha in acervo.para_local('acervo-ba')}

        self.assertNotIn('oxigenio', variaveis)
        self.assertNotIn('kd490', variaveis)

    def test_periodo_e_contagem_saem_da_agregacao_e_nao_de_campo_gravado(self):
        linha = next(l for l in acervo.para_local('acervo-ba') if l['variavel'] == 'sst')

        self.assertEqual(linha['n_medicoes'], 2)
        self.assertEqual(linha['data_inicio'], date(2020, 1, 1))
        self.assertEqual(linha['data_fim'], date(2026, 7, 24))

    def test_baa_aparece_como_alvo_e_nao_como_entrada(self):
        """🚨 O mal-entendido mais caro que esta tabela poderia induzir.

        `baa >= 3 em t+7` e o alvo declarado no artefato servido. Listado sem
        papel, ao lado de `sst`, ele passaria por entrada do modelo.
        """
        linha = next(l for l in acervo.para_local('acervo-ba') if l['variavel'] == 'baa')

        self.assertEqual(linha['papel'], acervo.ALVO)
        self.assertFalse(linha['entra_no_modelo'])

    def test_variavel_coletada_fora_do_modelo_diz_que_esta_fora(self):
        linha = next(l for l in acervo.para_local('acervo-ba') if l['variavel'] == 'hotspot')

        self.assertFalse(linha['entra_no_modelo'])
        self.assertTrue(linha['motivo'])

    def test_as_quatro_do_modelo_servido_sao_marcadas_como_entrada(self):
        no_modelo = {
            l['variavel'] for l in acervo.para_local('acervo-ba') if l['entra_no_modelo']
        }

        self.assertEqual(no_modelo, {'sst', 'dhw', 'salinidade'})

    def test_entradas_do_modelo_vem_primeiro(self):
        papeis = [linha['papel'] for linha in acervo.para_local('acervo-ba')]

        self.assertEqual(papeis[:3], [acervo.FEATURE] * 3)

    def test_nome_e_unidade_saem_das_choices_do_modelo(self):
        """⚠️ Derivados de `VARIAVEL_CHOICES`, nunca redigitados: uma segunda
        lista de rotulos diverge da primeira na proxima variavel nova."""
        linha = next(l for l in acervo.para_local('acervo-ba') if l['variavel'] == 'salinidade')

        self.assertEqual(linha['nome'], 'Salinidade')
        self.assertEqual(linha['unidade'], 'PSU')

    def test_cada_numero_vem_com_a_consulta_que_o_devolve(self):
        """Numero anunciado sem forma de conferir e afirmacao sem recibo."""
        linha = next(l for l in acervo.para_local('acervo-ba') if l['variavel'] == 'sst')

        self.assertEqual(linha['consulta'], '/api/medicoes/?local=acervo-ba&variavel=sst')

    def test_a_fonte_de_cada_variavel_viaja_junto(self):
        linha = next(l for l in acervo.para_local('acervo-ba') if l['variavel'] == 'salinidade')

        self.assertEqual(linha['fontes'], ['copernicus'])

    def test_local_sem_medicao_devolve_lista_vazia(self):
        vazio = LocalRecife.objects.create(
            slug='vazio-rn', nome='Vazio', estado='Rio Grande do Norte',
            cidade='Maxaranguape',
        )

        self.assertEqual(acervo.para_local(vazio.slug), [])


@override_settings(OFFLINE_MODE=False)
class DetalheDoLocalNaApiTests(TestCase):
    """O que `/api/locais/<slug>/` passou a devolver."""

    def setUp(self):
        self.local = LocalRecife.objects.create(
            slug='ficha-ba', nome='Ficha', estado='Bahia', cidade='Caravelas',
            latitude=-17.972, longitude=-38.688,
            fonte_coordenadas='ICMBio',
            profundidade_media_m=10.0,
            area_uc_km2=879.43,
            fonte_area_uc='ICMBio - 87.943 ha, Dec. 88.218/1983',
        )
        _medicao(self.local, 'sst', date(2026, 7, 24), unidade='°C')

    def _detalhe(self):
        resposta = self.client.get(
            reverse('local_recife_detail', kwargs={'slug': self.local.slug})
        )
        self.assertEqual(resposta.status_code, 200)
        return resposta.json()

    def test_profundidade_e_area_saem_do_django_admin_para_a_api(self):
        """🚨 Estavam no modelo desde a migracao `0014` e nunca num serializer.
        Nenhuma previsao usa os dois campos — por isso a ausencia nao quebrava
        teste nenhum."""
        detalhe = self._detalhe()

        self.assertEqual(detalhe['profundidade_media_m'], 10.0)
        self.assertEqual(detalhe['area_uc_km2'], 879.43)

    def test_cada_area_viaja_com_a_propria_fonte(self):
        """🚨 O numero sozinho nao e citavel, e pior: 879,43 km² sem "e o
        parque, nao o recife" e lido como area de recife. Ver migracao 0031."""
        detalhe = self._detalhe()

        self.assertIn('87.943 ha', detalhe['fonte_area_uc'])
        self.assertIn('area_recifal_km2', detalhe)
        self.assertIn('fonte_area_recifal', detalhe)

    def test_coordenada_vem_com_a_origem_junto(self):
        detalhe = self._detalhe()

        self.assertEqual(detalhe['fonte_coordenadas'], 'ICMBio')

    def test_o_acervo_completo_vem_no_detalhe(self):
        detalhe = self._detalhe()

        self.assertEqual(
            [linha['variavel'] for linha in detalhe['acervo']], ['sst'],
        )

    def test_a_lista_nao_carrega_o_acervo(self):
        """⚠️ Seriam N locais chamando a mesma agregacao numa pagina que nao a
        usa."""
        resposta = self.client.get(reverse('local_recife_list'))

        self.assertEqual(resposta.status_code, 200)
        self.assertNotIn('acervo', resposta.json()[0])

    def test_a_lista_carrega_a_ficha_fisica(self):
        """O cartao nao mostra profundidade hoje, mas a ficha e do **local** —
        deixa-la so no detalhe repetiria a decisao que criou o defeito."""
        resposta = self.client.get(reverse('local_recife_list'))

        self.assertIn('profundidade_media_m', resposta.json()[0])


class AreasSemeadasTests(TestCase):
    """Os valores que a migracao `0031` gravou, e os que ela deixou nulos.

    🚨 **Os nulos sao o conteudo deste teste, tanto quanto os numeros.** Tres
    locais nao sao unidades de conservacao — sao feicoes recifais dentro de UCs
    maiores. A "correcao" obvia para quem vier depois e preencher com a area da
    APA que os contem, e ela transformaria o parracho de Maracajau num poligono
    de 1.360 km². Este teste existe para essa correcao falhar alto.
    """

    # Nao sao UC propria: dentro da APA dos Recifes de Corais (RN), dentro da
    # APA Costa dos Corais, e sem protecao legal vigente, respectivamente.
    SEM_UC_PROPRIA = (
        'parrachos-de-maracajau-rn', 'porto-de-galinhas-pe', 'picaozinho-pb',
    )

    def test_area_da_uc_veio_com_fonte_em_todos_os_que_tem_numero(self):
        """Nao ha area sem fonte. A regra vale para os 10, e o teste nao lista
        quais tem numero de proposito — um local novo com area e sem fonte
        precisa quebrar aqui."""
        for local in LocalRecife.objects.all():
            if local.area_uc_km2 is not None:
                self.assertTrue(
                    local.fonte_area_uc,
                    f'{local.slug} tem area de UC sem fonte registrada',
                )

    def test_abrolhos_guarda_o_parque_e_nao_o_banco(self):
        """🚨 O numero que quase entrou errado.

        Abrolhos tem quatro areas publicadas: ~8 km² de recife mapeado,
        879,43 km² de parque, 6.000 km² de ecossistema recifal do banco norte e
        45.000 km² de Banco. `area_uc_km2` e a segunda — e a fonte diz qual.
        """
        local = LocalRecife.objects.filter(slug='abrolhos-ba').first()
        if local is None:
            self.skipTest('banco sem o seed de locais')

        self.assertAlmostEqual(local.area_uc_km2, 879.43, places=2)
        self.assertIn('87.943 ha', local.fonte_area_uc)

    def test_feicao_recifal_dentro_de_uc_maior_nao_herda_a_area_da_uc(self):
        """🚨 Gravar aqui a area da APA que contem o local seria atribuir a
        area do continente a ilha."""
        for slug in self.SEM_UC_PROPRIA:
            local = LocalRecife.objects.filter(slug=slug).first()
            if local is None:
                continue
            self.assertIsNone(
                local.area_uc_km2,
                f'{slug} nao e unidade de conservacao propria',
            )

    def test_nenhuma_area_recifal_foi_afirmada_sem_fonte_conferida(self):
        """⚠️ Ha um numero circulando para Abrolhos (~8 km², WorldView-2), mas a
        publicacao esta atras de paywall e autores/ano/DOI nao foram
        conferidos. Gravar assim repetiria a §3.1 do FONTES — referencia nao
        identificada usada como dado."""
        for local in LocalRecife.objects.all():
            if local.area_recifal_km2 is not None:
                self.assertTrue(
                    local.fonte_area_recifal,
                    f'{local.slug} tem area recifal sem fonte registrada',
                )


@override_settings(OFFLINE_MODE=False)
class ProcedenciaDaFotoDoLocalTests(TestCase):
    """A foto do recife, e de quem ela e (migracao `0030`).

    🚨 A migracao `0026` corrigiu a proveniencia das fotos de **especie** e
    parou ali. `LocalRecife.imagem` aparece no topo da pagina do recife e no
    cartao da lista, e nao havia nem campo para dizer de onde veio — o que nao
    tem campo nao aparece em auditoria de campo errado.
    """

    def _local(self, **campos):
        return LocalRecife.objects.create(
            slug='foto-ba', nome='Foto', estado='Bahia', cidade='Caravelas',
            **campos,
        )

    def _exportado(self, **campos):
        local = self._local(**campos)
        recifes = build_sync_payload()['recifes']
        return next(r for r in recifes if r['slug'] == local.slug)

    def test_a_api_serve_os_tres_campos(self):
        self._local(
            imagem='recifes/abrolhos.jpg',
            credito_imagem='ICMBio',
            fonte_imagem_url='https://www.gov.br/icmbio/exemplo',
            local_captura_foto='Parcel dos Abrolhos, BA',
        )

        detalhe = self.client.get(
            reverse('local_recife_detail', kwargs={'slug': 'foto-ba'})
        ).json()

        self.assertEqual(detalhe['credito_imagem'], 'ICMBio')
        self.assertEqual(detalhe['local_captura_foto'], 'Parcel dos Abrolhos, BA')
        self.assertTrue(detalhe['imagem_tem_procedencia'])

    def test_sem_credito_a_api_diz_que_nao_ha_procedencia(self):
        """⚠️ A API continua servindo `imagem_url` — quem decide o que afirmar
        e a tela, e `imagem_tem_procedencia` e o que ela usa para decidir.
        Mesma divisao ja escolhida para a foto de especie."""
        self._local(imagem='recifes/sem_credito.jpg')

        detalhe = self.client.get(
            reverse('local_recife_detail', kwargs={'slug': 'foto-ba'})
        ).json()

        self.assertFalse(detalhe['imagem_tem_procedencia'])
        self.assertEqual(detalhe['credito_imagem'], '')

    def test_foto_sem_credito_nao_entra_na_copia_versionada(self):
        """A mesma regra da foto de especie, um modelo adiante: o fallback e o
        que o site mostra quando a API cai, e um dado sem lastro dentro de um
        `.js` sobrevive a limpeza do banco."""
        exportado = self._exportado(imagem='recifes/sem_credito.jpg')

        self.assertEqual(exportado['imagem_url'], '')
        self.assertEqual(exportado['credito_imagem'], '')

    def test_com_credito_a_foto_inteira_passa_para_a_copia_versionada(self):
        exportado = self._exportado(
            imagem='recifes/abrolhos.jpg',
            credito_imagem='ICMBio',
            fonte_imagem_url='https://www.gov.br/icmbio/exemplo',
            local_captura_foto='Parcel dos Abrolhos, BA',
        )

        self.assertIn('abrolhos.jpg', exportado['imagem_url'])
        self.assertEqual(exportado['credito_imagem'], 'ICMBio')
        self.assertEqual(exportado['local_captura_foto'], 'Parcel dos Abrolhos, BA')

    def test_a_ficha_fisica_chega_ao_fallback_offline(self):
        """Sao dados **do local**, nao da serie: continuam verdadeiros com a
        API fora do ar, pelo mesmo motivo que `motivo_sem_serie` continua."""
        exportado = self._exportado(
            latitude=-17.972, longitude=-38.688,
            fonte_coordenadas='ICMBio',
            profundidade_media_m=10.0,
            area_uc_km2=879.43,
            fonte_area_uc='ICMBio - 87.943 ha, Dec. 88.218/1983',
        )

        self.assertEqual(exportado['latitude'], -17.972)
        self.assertEqual(exportado['fonte_coordenadas'], 'ICMBio')
        self.assertEqual(exportado['profundidade_media_m'], 10.0)
        self.assertEqual(exportado['area_uc_km2'], 879.43)

    def test_a_fonte_da_area_acompanha_a_area_na_copia_versionada(self):
        """⚠️ Numero sem lastro dentro de um `.js` sobrevive a limpeza do banco
        — a combinacao que a §2.1 do FONTES ensinou a evitar."""
        exportado = self._exportado(
            area_uc_km2=879.43,
            fonte_area_uc='ICMBio - 87.943 ha, Dec. 88.218/1983',
        )

        self.assertIn('87.943 ha', exportado['fonte_area_uc'])

    def test_campo_nao_registrado_sai_nulo_e_nao_zero(self):
        """⚠️ Zero em profundidade e uma afirmacao fisica ("recife na
        superficie"); nulo e "ninguem mediu". O pipeline legado ja cometeu essa
        troca gravando pH 0 e salinidade 0."""
        exportado = self._exportado()

        self.assertIsNone(exportado['profundidade_media_m'])
        self.assertIsNone(exportado['area_uc_km2'])
        self.assertIsNone(exportado['area_recifal_km2'])
