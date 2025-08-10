/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'status-green': '#10b981',
        'status-red': '#ef4444', 
        'status-yellow': '#f59e0b',
        'status-orange': '#f97316',
        'status-gray': '#6b7280',
      }
    },
  },
  plugins: [],
}
