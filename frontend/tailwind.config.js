/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        obsidian: {
          DEFAULT: '#08080a',
          base: '#050507',
          surface: '#0d0d12',
          card: '#121218',
          border: 'rgba(255, 255, 255, 0.08)',
          subtle: 'rgba(255, 255, 255, 0.04)',
        },
        crimson: {
          DEFAULT: '#ef4444',
          glow: 'rgba(239, 68, 68, 0.3)',
          50: '#fef2f2',
          100: '#fee2e2',
          200: '#fecaca',
          300: '#fca5a5',
          400: '#f87171',
          500: '#ef4444',
          600: '#dc2626',
          700: '#b91c1c',
          800: '#991b1b',
          900: '#7f1d1d',
          950: '#450a0a',
        },
        vscode: {
          bg: '#08080a',
          sidebar: '#0d0d12',
          surface: '#121218',
          border: 'rgba(255, 255, 255, 0.08)',
          text: '#f3f4f6',
          muted: '#9ca3af',
          accent: '#ef4444',
          'accent-hover': '#dc2626',
          'accent-light': 'rgba(239, 68, 68, 0.15)',
          green: '#22c55e',
          yellow: '#eab308',
          red: '#ef4444',
          blue: '#3b82f6',
          purple: '#a855f7',
        },
      },
      boxShadow: {
        'glow-red': '0 0 25px -5px rgba(239, 68, 68, 0.35)',
        'glow-red-lg': '0 0 50px -10px rgba(239, 68, 68, 0.45)',
        'glow-subtle': '0 0 20px 0 rgba(239, 68, 68, 0.12)',
      },
      backgroundImage: {
        'red-radial': 'radial-gradient(ellipse at top, rgba(239, 68, 68, 0.18), transparent 70%)',
        'crimson-gradient': 'linear-gradient(135deg, #ef4444 0%, #b91c1c 100%)',
      },
    },
  },
  plugins: [],
};
