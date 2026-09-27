/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        surface: '#0f1623',
        panel: '#161e2e',
        card: '#1c2639',
        border: '#2a3750',
        accent: '#3b82f6',
        danger: '#ef4444',
        warning: '#f59e0b',
        success: '#22c55e',
        muted: '#64748b',
      },
    },
  },
  plugins: [],
}
