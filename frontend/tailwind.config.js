/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'ui-sans-serif', 'system-ui', '-apple-system', '"Segoe UI"', 'sans-serif'],
      },
      colors: {
        // The product's colours. Status colours stay emerald, amber, and rose.
        navy: {
          600: '#24467c',
          700: '#1a3563',
          800: '#12274b',
          900: '#0b1c38',
          950: '#071327',
        },
        brand: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
        },
        accent: {
          100: '#cffafe',
          300: '#67e8f9',
          500: '#06b6d4',
          700: '#0e7490',
        },
      },
    },
  },
  plugins: [],
};
