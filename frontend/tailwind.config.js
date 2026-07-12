/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        base: {
          950: '#080D17',
          900: '#0B1220',
          850: '#0F1728',
          800: '#121A2B',
          700: '#1B253B',
          600: '#293552',
          500: '#3D4A6B',
        },
        ink: {
          100: '#E8ECF4',
          300: '#B7C0D8',
          500: '#8793AD',
          700: '#5B6780',
        },
        signal: {
          critical: '#E5484D',
          high: '#F5A623',
          medium: '#F2C94C',
          low: '#34D399',
          info: '#4F8EF7',
        },
        accent: {
          DEFAULT: '#22D3C9',
          dim: '#0F9C93',
          glow: '#5EF2E6',
        },
      },
      fontFamily: {
        display: ['"Space Grotesk"', 'sans-serif'],
        body: ['Inter', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'monospace'],
      },
      boxShadow: {
        panel: '0 1px 0 0 rgba(255,255,255,0.03) inset, 0 8px 24px -12px rgba(0,0,0,0.5)',
        glow: '0 0 0 1px rgba(34,211,201,0.35), 0 0 24px -4px rgba(34,211,201,0.35)',
      },
      backgroundImage: {
        grid: 'linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px)',
      },
      backgroundSize: {
        grid: '28px 28px',
      },
    },
  },
  plugins: [],
}
