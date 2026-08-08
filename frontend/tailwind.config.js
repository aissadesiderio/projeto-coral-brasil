/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        "./src/**/*.{js,jsx,ts,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                ocean: {
                    // Era '#3C6876'; unificado com o '#2b6978' que Header, Home,
                    // CardRecife e RecifesPage já usavam solto — as duas eram a
                    // mesma cor de marca digitada duas vezes.
                    dark: '#2b6978',
                    light: '#9FBDBC',
                },
                sand: {
                    // Une '#ffefeb' (body/footer/gradiente) e '#fff6f4'
                    // (RecifesPage/CardRecife), que eram a mesma cor com dois
                    // hex diferentes.
                    lightest: '#ffefeb',
                    light: '#ECE0D9',
                    dark: '#E0B998',
                },
                terra: '#D47046',
            },
            // Tamanhos que apareciam soltos como text-[1.9rem] etc. em Header,
            // HomePage, CardRecife e RecifesPage — cada um usado em um lugar só,
            // valor preservado, agora nomeado num lugar central em vez de
            // reescrito a cada arquivo.
            fontSize: {
                '3xs': '0.625rem',    // 10px — PainelPredicao, selos e rotulos minimos
                '2xs': '0.6875rem',   // 11px — PainelPredicao, legendas finas
                micro: '0.58rem',     // Header — legenda abaixo do logotipo
                'brand-sm': '1.55rem',  // Header — logotipo, mobile
                'card-title': '1.6rem', // CardRecife — titulo do cartao
                'heading-sm': '1.9rem', // Header — logotipo desktop; HomePage — h1 mobile
                heading: '2.4rem',      // HomePage — h1, tablet
                'heading-lg': '2.75rem',// HomePage — h1, desktop
                'heading-xl': '3.15rem',// RecifesPage — titulo da pagina, desktop
            },
        },
    },
    plugins: [],
}