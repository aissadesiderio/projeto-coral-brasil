/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        "./src/**/*.{js,jsx,ts,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                ocean: {
                    // 🚨 São duas cores com papéis distintos desde o redesenho
                    // "3a" (13/08/2026), e trocá-las apaga a hierarquia:
                    // `deep` é o chrome — cabeçalho, faixas escuras, rodapé,
                    // botão primário. `dark` é o traço de dado e o link em
                    // fundo claro (a curva de SST usa o mesmo hex).
                    deep: '#17414c',
                    dark: '#2b6978',
                    light: '#9FBDBC',
                },
                sand: {
                    lightest: '#ffefeb',  // fundo da página
                    light: '#ECE0D9',     // moldura de imagem sem foto
                    dark: '#E0B998',
                    // As três abaixo entraram com o 3a e não são decoração: cada
                    // uma marca um tipo de conteúdo. `tabela` é cabeçalho de
                    // coluna, `nota` é a linha de proveniência no pé de uma
                    // tabela, `aviso` é o bloco de procedência obrigatória.
                    tabela: '#f8e7e0',
                    nota: '#fffaf7',
                    aviso: '#fff6f1',
                },
                terra: {
                    DEFAULT: '#D47046',
                    // Terra escurecido até passar em contraste sobre `sand.aviso`
                    // — o #D47046 sobre #fff6f1 fica em 2,6:1 e não serve para
                    // texto.
                    dark: '#8A4A22',
                },
            },
            fontFamily: {
                // Newsreader carrega os títulos, Inter o texto corrido e Plex
                // Mono tudo o que é medida: rótulo de coluna, data, percentual,
                // coordenada. A separação é o que faz um número parecer
                // instrumento e não enfeite.
                sans: ['Inter', 'Segoe UI', 'sans-serif'],
                serif: ['Newsreader', 'Georgia', 'serif'],
                mono: ['IBM Plex Mono', 'ui-monospace', 'monospace'],
            },
            fontSize: {
                '3xs': '0.625rem',    // 10px — rotulos mono minimos
                '2xs': '0.6875rem',   // 11px — legendas finas
                micro: '0.58rem',
                'brand-sm': '1.55rem',
                'card-title': '1.6rem',
                'heading-sm': '1.9rem',
                heading: '2.4rem',
                'heading-lg': '2.75rem',
                'heading-xl': '3.15rem',
            },
            boxShadow: {
                // A sombra do 3a e sempre projetada para cima e curta: o cartao
                // encosta na areia em vez de flutuar sobre ela.
                superficie: '0 14px 34px -22px rgba(23,65,76,0.35)',
                tela: '0 30px 60px -20px rgba(23,65,76,0.25)',
            },
        },
    },
    plugins: [],
}
