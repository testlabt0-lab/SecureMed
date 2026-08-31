/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
          950: '#172554',
        },
        medical: {
          50: '#f0fdfa',
          100: '#ccfbf1',
          200: '#99f6e4',
          300: '#5eead4',
          400: '#2dd4bf',
          500: '#14b8a6',
          600: '#0d9488',
          700: '#0f766e',
          800: '#115e59',
          900: '#134e4a',
        },
        security: {
          50: '#fef2f2',
          500: '#ef4444',
          600: '#dc2626',
          700: '#b91c1c',
        },
        navy: {
          700: '#1e293b',
          800: '#0f172a',
          900: '#0b1120',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        arabic: ['Noto Sans Arabic', 'sans-serif'],
        heading: ['Cairo', 'Noto Sans Arabic', 'system-ui', 'sans-serif'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'bounce-once': 'bounce 0.5s ease-out',
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-in': 'slideIn 0.3s ease-out',
        'fade-in-up': 'fadeInUp 0.6s cubic-bezier(0.22, 1, 0.36, 1) both',
        'float': 'float 7s ease-in-out infinite',
        'float-slow': 'floatSlow 11s ease-in-out infinite',
        'float-fast': 'float 5s ease-in-out infinite',
        'heartbeat': 'heartbeat 1.6s ease-in-out infinite',
        'shimmer': 'shimmer 2.6s linear infinite',
        'gradient': 'gradientShift 8s ease infinite',
        'gradient-x': 'gradientShift 5s ease infinite',
        'spin-slow': 'spin 22s linear infinite',
        'spin-slower': 'spin 40s linear infinite',
        'ken-burns': 'kenBurns 24s ease-in-out infinite alternate',
        'blob': 'blob 12s ease-in-out infinite',
        'blob-alt': 'blobAlt 16s ease-in-out infinite',
        'ecg': 'ecgDash 3.2s linear infinite',
        'pulse-ring': 'pulseRing 2.4s cubic-bezier(0.16, 1, 0.3, 1) infinite',
        'glow': 'glow 2.6s ease-in-out infinite',
        'scan': 'scan 3.4s ease-in-out infinite',
        'wiggle': 'wiggle 2.4s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideIn: {
          '0%': { transform: 'translateX(100%)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
        fadeInUp: {
          '0%': { opacity: '0', transform: 'translateY(24px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0) translateX(0)' },
          '25%': { transform: 'translateY(-18px) translateX(6px)' },
          '50%': { transform: 'translateY(-32px) translateX(-4px)' },
          '75%': { transform: 'translateY(-14px) translateX(8px)' },
        },
        floatSlow: {
          '0%, 100%': { transform: 'translateY(0) translateX(0) rotate(0deg)' },
          '33%': { transform: 'translateY(-26px) translateX(14px) rotate(4deg)' },
          '66%': { transform: 'translateY(12px) translateX(-12px) rotate(-3deg)' },
        },
        heartbeat: {
          '0%': { transform: 'scale(1)' },
          '14%': { transform: 'scale(1.16)' },
          '28%': { transform: 'scale(1)' },
          '42%': { transform: 'scale(1.16)' },
          '70%': { transform: 'scale(1)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        gradientShift: {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
        },
        kenBurns: {
          '0%': { transform: 'scale(1) translate(0, 0)' },
          '100%': { transform: 'scale(1.14) translate(-1.5%, -2%)' },
        },
        blob: {
          '0%, 100%': { borderRadius: '58% 42% 55% 45% / 55% 48% 52% 45%', transform: 'translate(0, 0) scale(1)' },
          '33%': { borderRadius: '45% 55% 48% 52% / 48% 55% 45% 52%', transform: 'translate(28px, -38px) scale(1.08)' },
          '66%': { borderRadius: '52% 48% 42% 58% / 52% 42% 58% 48%', transform: 'translate(-20px, 22px) scale(0.94)' },
        },
        blobAlt: {
          '0%, 100%': { borderRadius: '45% 55% 52% 48% / 52% 45% 55% 48%', transform: 'translate(0, 0) scale(1)' },
          '50%': { borderRadius: '58% 42% 45% 55% / 45% 58% 42% 55%', transform: 'translate(-34px, 30px) scale(1.1)' },
        },
        ecgDash: {
          '0%': { strokeDashoffset: '1000' },
          '100%': { strokeDashoffset: '0' },
        },
        pulseRing: {
          '0%': { transform: 'scale(0.85)', opacity: '0.75' },
          '80%, 100%': { transform: 'scale(1.9)', opacity: '0' },
        },
        glow: {
          '0%, 100%': { filter: 'drop-shadow(0 0 4px rgba(37, 99, 235, 0.35))' },
          '50%': { filter: 'drop-shadow(0 0 16px rgba(13, 148, 136, 0.65))' },
        },
        scan: {
          '0%, 100%': { transform: 'translateY(-100%)' },
          '50%': { transform: 'translateY(100%)' },
        },
        wiggle: {
          '0%, 100%': { transform: 'rotate(-4deg)' },
          '50%': { transform: 'rotate(4deg)' },
        },
      },
      boxShadow: {
        'glow-primary': '0 0 24px rgba(37, 99, 235, 0.35)',
        'glow-medical': '0 0 24px rgba(13, 148, 136, 0.35)',
        'card': '0 1px 3px rgba(15, 23, 42, 0.06), 0 8px 24px -8px rgba(15, 23, 42, 0.12)',
        'card-hover': '0 4px 8px rgba(15, 23, 42, 0.06), 0 20px 44px -12px rgba(37, 99, 235, 0.25)',
        'inner-light': 'inset 0 1px 0 rgba(255, 255, 255, 0.12)',
      },
      backgroundImage: {
        'mesh-medical':
          'radial-gradient(at 12% 18%, rgba(37, 99, 235, 0.16) 0px, transparent 55%), ' +
          'radial-gradient(at 85% 12%, rgba(13, 148, 136, 0.15) 0px, transparent 50%), ' +
          'radial-gradient(at 78% 88%, rgba(99, 102, 241, 0.14) 0px, transparent 52%), ' +
          'radial-gradient(at 20% 82%, rgba(6, 182, 212, 0.12) 0px, transparent 48%)',
      },
    },
  },
  plugins: [],
};
