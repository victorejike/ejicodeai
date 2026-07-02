/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        vscode: {
          bg: '#1e1e1e',
          sidebar: '#252526',
          surface: '#2d2d30',
          border: '#3e3e42',
          text: '#cccccc',
          muted: '#858585',
          accent: '#0e639c',
          'accent-hover': '#1177bb',
          'accent-light': '#264f78',
          green: '#4ec9b0',
          yellow: '#dcdcaa',
          red: '#f44747',
          blue: '#569cd6',
          purple: '#c586c0',
        },
      },
    },
  },
  plugins: [],
};
