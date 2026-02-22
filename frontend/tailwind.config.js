/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f4f7f4',
          100: '#e2ebe2',
          200: '#c5d7c5',
          300: '#9dba9d',
          400: '#6f966f',
          500: '#527a52',
          600: '#3d5e3d',
          700: '#2d472d',
          800: '#263a26',
          900: '#1f2f1f',
        },
        cream: {
          50: '#fdfcfb',
          100: '#faf8f5',
          200: '#f5f1ec',
          300: '#ece7e0',
          400: '#e0d9d0',
          500: '#c4bbb0',
        },
        warm: {
          50: '#faf9f7',
          100: '#f0eeeb',
          200: '#e8e5e0',
          300: '#d4cfc8',
          400: '#a8a198',
          500: '#7a746b',
          600: '#5c574f',
          700: '#3d3a35',
          800: '#2a2825',
          900: '#1a1917',
        },
      },
    },
  },
  plugins: [],
}
