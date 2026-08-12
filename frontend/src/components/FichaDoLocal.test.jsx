/**
 * Testes da ficha fisica do recife.
 *
 * 🚨 O motivo de existirem: `profundidade_media_m` e `area_km2` estavam no
 * modelo desde a migracao `0014` e nunca sairam do Django admin. Nenhuma
 * previsao usa os dois campos — e foi exatamente por isso que a ausencia deles
 * nao quebrou nada e ninguem reparou.
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
  area_km2: 913,
};

test('mostra profundidade e area, que nenhuma previsao usa', () => {
  render(<FichaDoLocal local={COMPLETO} />);

  expect(screen.getByText('10,0 m')).toBeInTheDocument();
  expect(screen.getByText('913,0 km²')).toBeInTheDocument();
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
        area_km2: null,
      }}
    />,
  );

  expect(screen.getAllByText('Nao registrado')).toHaveLength(3);
});

test('profundidade zero nao vira "nao registrado"', () => {
  // ⚠️ Zero e uma afirmacao fisica; nulo e a ausencia dela. Um `||` no lugar
  // do teste de nulo trocaria uma pela outra.
  render(<FichaDoLocal local={{ ...COMPLETO, profundidade_media_m: 0 }} />);

  expect(screen.getByText('0,0 m')).toBeInTheDocument();
});
