/** @type {import('tailwindcss').Config} */
module.exports = {
content: ["./src/**/*.{html,js}",
"frontend/templates/**/*.html",
"frontend/templates/**/*.html",
"frontend/templates/**/**/*.html",
"frontend/templates/**/**/**/*.html",
"frontend/templates/**/*.js",
"frontend/templates/**/*.js",
"frontend/templates/**/**/*.js",

],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
    },
  },
  plugins: [],
}

