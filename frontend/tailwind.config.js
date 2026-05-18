/** @type {import('tailwindcss').Config} */
module.exports = {
    darkMode: ["class"],
    content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html"
  ],
  theme: {
  	extend: {
  		borderRadius: {
  			lg: 'var(--radius)',
  			md: 'calc(var(--radius) - 2px)',
  			sm: 'calc(var(--radius) - 4px)'
  		},
  		boxShadow: {
  			'sm': 'var(--shadow-sm)',
  			'md': 'var(--shadow-md)',
  			'lg': 'var(--shadow-lg)',
  			'xl': 'var(--shadow-xl)',
  			'glow': 'var(--shadow-glow)',
  			'glow-gold': 'var(--shadow-glow-gold)',
  			'gold': 'var(--shadow-gold)',
  		},
  		colors: {
  			background: 'hsl(var(--background))',
  			foreground: 'hsl(var(--foreground))',
  			card: {
  				DEFAULT: 'hsl(var(--card))',
  				foreground: 'hsl(var(--card-foreground))'
  			},
  			popover: {
  				DEFAULT: 'hsl(var(--popover))',
  				foreground: 'hsl(var(--popover-foreground))'
  			},
  			primary: {
  				DEFAULT: 'hsl(var(--primary))',
  				foreground: 'hsl(var(--primary-foreground))'
  			},
  			secondary: {
  				DEFAULT: 'hsl(var(--secondary))',
  				foreground: 'hsl(var(--secondary-foreground))'
  			},
  			muted: {
  				DEFAULT: 'hsl(var(--muted))',
  				foreground: 'hsl(var(--muted-foreground))'
  			},
  			accent: {
  				DEFAULT: 'hsl(var(--accent))',
  				foreground: 'hsl(var(--accent-foreground))'
  			},
  			destructive: {
  				DEFAULT: 'hsl(var(--destructive))',
  				foreground: 'hsl(var(--destructive-foreground))'
  			},
  			gold: {
  				DEFAULT: 'hsl(var(--gold))',
  				soft: 'hsl(var(--gold-soft))',
  				deep: 'hsl(var(--gold-deep))',
  				foreground: 'hsl(var(--gold-foreground))',
  			},
  			navy: {
  				deep: 'hsl(var(--navy-deep))',
  				mid: 'hsl(var(--navy-mid))',
  				surface: 'hsl(var(--navy-surface))',
  				border: 'hsl(var(--navy-border))',
  			},
  			success: {
  				DEFAULT: 'hsl(var(--success))',
  				foreground: 'hsl(var(--success-foreground))'
  			},
  			warning: {
  				DEFAULT: 'hsl(var(--warning))',
  				foreground: 'hsl(var(--warning-foreground))'
  			},
  			info: {
  				DEFAULT: 'hsl(var(--info))',
  				foreground: 'hsl(var(--info-foreground))'
  			},
  			border: 'hsl(var(--border))',
  			input: 'hsl(var(--input))',
  			ring: 'hsl(var(--ring))',
  			chart: {
  				'1': 'hsl(var(--chart-1))',
  				'2': 'hsl(var(--chart-2))',
  				'3': 'hsl(var(--chart-3))',
  				'4': 'hsl(var(--chart-4))',
  				'5': 'hsl(var(--chart-5))'
  			}
  		},
   		keyframes: {
   			'accordion-down': {
   				from: {
   					height: '0'
   				},
   				to: {
   					height: 'var(--radix-accordion-content-height)'
   				}
   			},
   			'accordion-up': {
   				from: {
   					height: 'var(--radix-accordion-content-height)'
   				},
   				to: {
   					height: '0'
   				}
   			},
   			'skeleton-pulse': {
   				'0%, 100%': { opacity: '0.4' },
   				'50%': { opacity: '0.8' },
   			},
   			'fade-in': {
   				from: { opacity: '0', transform: 'translateY(4px)' },
   				to: { opacity: '1', transform: 'translateY(0)' },
   			},
   			'float': {
   				'0%, 100%': { transform: 'translateY(0)' },
   				'50%': { transform: 'translateY(-10px)' },
   			},
   			'float-delayed': {
   				'0%, 100%': { transform: 'translateY(0)' },
   				'50%': { transform: 'translateY(-12px)' },
   			},
   			'pulse-glow': {
   				'0%, 100%': { opacity: '0.6', filter: 'brightness(1)' },
   				'50%': { opacity: '1', filter: 'brightness(1.2)' },
   			},
   			'heartbeat': {
   				'0%, 100%': { transform: 'scale(1)' },
   				'15%': { transform: 'scale(1.15)' },
   				'30%': { transform: 'scale(1)' },
   				'45%': { transform: 'scale(1.08)' },
   				'60%': { transform: 'scale(1)' },
   			},
   			'spin-slow': {
   				to: { transform: 'rotate(360deg)' },
   			},
   		},
   		animation: {
   			'accordion-down': 'accordion-down 0.2s ease-out',
   			'accordion-up': 'accordion-up 0.2s ease-out',
   			'skeleton-pulse': 'skeleton-pulse 1.5s ease-in-out infinite',
   			'fade-in': 'fade-in 0.25s ease-out',
   			'float': 'float 4s ease-in-out infinite',
   			'float-delayed': 'float-delayed 5s ease-in-out infinite',
   			'pulse-glow': 'pulse-glow 2s ease-in-out infinite',
   			'heartbeat': 'heartbeat 1.4s ease-in-out infinite',
   			'spin-slow': 'spin-slow 8s linear infinite',
   		}
  	}
  },
  plugins: [require("tailwindcss-animate")],
};
