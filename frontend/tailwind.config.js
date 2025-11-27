/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        "./src/**/*.{js,jsx,ts,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                ocean: {
                    dark: '#3C6876',
                    light: '#9FBDBC',
                },
                sand: {
                    light: '#ECE0D9',
                    dark: '#E0B998',
                },
                terra: '#D47046',
            },
            fontFamily: {
                poppins: ['Poppins', 'sans-serif'],
            }
        },
    },
    plugins: [],
}