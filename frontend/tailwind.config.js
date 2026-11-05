/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./worker/index.html",
    "./checkin/index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'mission': {
          50: '#fff6ea',
          100: '#fde8c8',
          200: '#f6d19a',
          300: '#f0b45a',
          400: '#e89224',
          500: '#e89224',
          600: '#c97a16',
          700: '#785510',
          800: '#0f0e13',
          900: '#0f0e13',
        }
      },
      fontFamily: {
        'sans': ['Roboto', 'system-ui', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
