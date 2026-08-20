/**
 * Testes da ficha fisica do recife.
 *
 * 🚨 O motivo de existirem: `profundidade_media_m` e a area estavam no modelo
 * desde a migracao `0014` e nunca sairam do Django admin. Nenhuma previsao usa
 * esses campos — e foi exatamente por isso que a ausencia deles nao quebrou
 * nada e ninguem reparou.
 *
 * ⚠️ O campo de area virou **dois** na migracao `0031` (`area_uc_km2` e
 * `area_recifal_km2`): o original dizia "zona recifal" e so tinha fonte para a
 * area da UC, que em Abrolhos e 110x maior que o recife medido.
 *
 * ⚠️ E a lacuna precisa continuar **escrita**. Esconder a linha vazia faria a
 * ficha ser lida como completa, e "10 m" e "ninguem mediu" sao afirmacoes
 * diferentes.
 */

import { render, screen } from '@testing-library/react';

import FichaDoLocal from './FichaDoLocal';

const COMPLETO = {
  nome: 'Abrolhos',
  estado: 'Bahia',
  cidade: 'Caravelas',
  latitude: -17.972,
  longitude: -38.688,
  fonte_coordenadas: 'Seed original do projeto',
  profundidade_media_m: 10,
  area_uc_km2: 879.43,
  fonte_area_uc: 'ICMBio - 87.943 ha, Dec. 88.218/1983',
  area_recifal_km2: null,
  fonte_area_recifal: '',
};

test('mostra profundidade e area, que nenhuma previsao usa', () => {
  render(<FichaDoLocal local={COMPLETO} />);

  expect(screen.getByText('10,0 m')).toBeInTheDocument();
  expect(screen.getByText('879,43 km²')).toBeInTheDocument();
});

/**
 * 🚨 As duas areas sao duas perguntas, com 110x entre elas em Abrolhos: 879,43
 * km² de parque contra ~8 km² de recife mapeado. Se este teste quebrar porque
 * alguem juntou as linhas de volta num campo so, o site volta a poder exibir a
 * area do parque sob o rotulo "recife" — o erro de categoria da §6.3 do FONTES.
 */
test('separa a area da UC da area recifal', () => {
  render(
    <FichaDoLocal
      local={{ ...COMPLETO, area_recifal_km2: 8, fonte_area_recifal: 'WorldView-2' }}
    />,
  );

  expect(screen.getByText('Area da unidade de conservacao')).toBeInTheDocument();
  expect(screen.getByText('Area recifal mapeada')).toBeInTheDocument();
  expect(screen.getByText('879,43 km²')).toBeInTheDocument();
  expect(screen.getByText('8,00 km²')).toBeInTheDocument();
});

test('cada area aparece com a sua propria fonte', () => {
  render(
    <FichaDoLocal
      local={{ ...COMPLETO, area_recifal_km2: 8, fonte_area_recifal: 'WorldView-2' }}
    />,
  );

  expect(screen.getByText('ICMBio - 87.943 ha, Dec. 88.218/1983')).toBeInTheDocument();
  expect(screen.getByText('WorldView-2')).toBeInTheDocument();
});

test('avisa que uma area nao se deduz da outra', () => {
  // ⚠️ Sem esta frase, quem ve 879,43 km² em cima e "Nao registrado" embaixo
  // conclui que o recife tem 879 km².
  render(<FichaDoLocal local={COMPLETO} />);

  expect(screen.getByText(/uma nao se deduz da outra/)).toBeInTheDocument();
});

test('a coordenada nunca aparece sem a origem', () => {
  render(<FichaDoLocal local={COMPLETO} />);

  // Ponto decimal de proposito: o par existe para ser colado num mapa, e com
  // virgula decimal os quatro separadores ficam iguais.
  expect(screen.getByText('-17.9720, -38.6880')).toBeInTheDocument();
  expect(
    screen.getByText('Origem: Seed original do projeto'),
  ).toBeInTheDocument();
});

test('coordenada sem origem registrada diz isso', () => {
  render(<FichaDoLocal local={{ ...COMPLETO, fonte_coordenadas: '' }} />);

  expect(screen.getByText('Origem nao registrada.')).toBeInTheDocument();
});

test('sem coordenada nenhuma, nao afirma origem de coordenada', () => {
  // ⚠️ Nos dois locais sem lat/lon, `fonte_coordenadas` guarda o **motivo da
  // ausencia**. Rotula-lo "Origem:" afirmaria que existe uma coordenada vinda
  // de algum lugar — e o motivo ja e dito por extenso pelo AvisoSemSerie.
  render(
    <FichaDoLocal
      local={{
        ...COMPLETO,
        latitude: null,
        longitude: null,
        fonte_coordenadas: 'Sem coordenada: e uma area, nao um ponto.',
      }}
    />,
  );

  expect(screen.queryByText(/^Origem:/)).not.toBeInTheDocument();
});

test('campo ausente e escrito, nao omitido', () => {
  render(
    <FichaDoLocal
      local={{
        ...COMPLETO,
        latitude: null,
        longitude: null,
        profundidade_media_m: null,
        area_uc_km2: null,
      }}
    />,
  );

  // Coordenadas, profundidade, area da UC e area recifal.
  expect(screen.getAllByText('Nao registrado')).toHaveLength(4);
});

test('profundidade zero nao vira "nao registrado"', () => {
  // ⚠️ Zero e uma afirmacao fisica; nulo e a ausencia dela. Um `||` no lugar
  // do teste de nulo trocaria uma pela outra.
  render(<FichaDoLocal local={{ ...COMPLETO, profundidade_media_m: 0 }} />);

  expect(screen.getByText('0,0 m')).toBeInTheDocument();
});
