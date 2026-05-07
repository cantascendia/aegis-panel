import tailwindcssAnimate from 'tailwindcss-animate';
import tailwindcssForm from '@tailwindcss/forms';
import tailwindcssAspectRatio from '@tailwindcss/aspect-ratio';
import tailwindcssTypography from '@tailwindcss/typography';
import { nextui } from '@nextui-org/react'

/** @type {import('tailwindcss').Config} */
const config = {
    darkMode: ["class"],
    content: [
        './pages/**/*.{ts,tsx}',
        './components/**/*.{ts,tsx}',
        './app/**/*.{ts,tsx}',
        './src/**/*.{ts,tsx}',
        "./node_modules/@nextui-org/theme/dist/**/*.{js,ts,jsx,tsx}",
    ],
    prefix: "",
    theme: {
        screens: {
            'sm': '0',
            'md': '768px',
            'lg': '1024px',
            'xl': '1280px',
        },
        container: {
            center: true,
            padding: "2rem",
            screens: {
                "2xl": "1400px",
            },
        },
        extend: {
            colors: {
                border: "hsl(var(--border))",
                input: "hsl(var(--input))",
                ring: "hsl(var(--ring))",
                background: "hsl(var(--background))",
                foreground: "hsl(var(--foreground))",
                primary: {
                    DEFAULT: "hsl(var(--primary))",
                    foreground: "hsl(var(--primary-foreground))",
                },
                secondary: {
                    DEFAULT: "hsl(var(--secondary))",
                    foreground: "hsl(var(--secondary-foreground))",
                },
                success: {
                    DEFAULT: "hsl(var(--success))",
                    foreground: "hsl(var(--success-foreground))",
                    accent: "hsl(var(--success-accent))",
                },
                destructive: {
                    DEFAULT: "hsl(var(--destructive))",
                    foreground: "hsl(var(--destructive-foreground))",
                    accent: "hsl(var(--destructive-accent))",
                },
                muted: {
                    DEFAULT: "hsl(var(--muted))",
                    foreground: "hsl(var(--muted-foreground))",
                },
                accent: {
                    DEFAULT: "hsl(var(--accent))",
                    foreground: "hsl(var(--accent-foreground))",
                },
                popover: {
                    DEFAULT: "hsl(var(--popover))",
                    foreground: "hsl(var(--popover-foreground))",
                },
                card: {
                    DEFAULT: "hsl(var(--card))",
                    foreground: "hsl(var(--card-foreground))",
                },
                // AEGIS fork — Nilou Network palette overrides on top of
                // Tailwind defaults. Many upstream Marzneshin components
                // hardcode `bg-gray-800` / `bg-indigo-700` / `bg-amber-200`
                // etc instead of semantic tokens, bypassing nilou-theme.css's
                // HSL var override. We remap the hardcoded palette entries
                // here so those components also inherit Nilou tones without
                // needing per-component edits.
                //
                // Source of truth: customer-portal/src/styles/tokens.css +
                // BRAND-GUIDELINES.md §2-3.
                gray: {
                    50:  '#f7f1e3',
                    100: '#efe6cf',
                    200: '#e8dfca',
                    300: '#d6c9a8',
                    400: '#a89878',
                    500: '#7a6c52',
                    600: '#5a4f3a',
                    700: '#3f3729',
                    800: '#2a2419',
                    900: '#1a1611',
                    950: '#0d0b08',
                },
                slate: {
                    50:  '#f7f1e3', 100: '#efe6cf', 200: '#e8dfca',
                    300: '#d6c9a8', 400: '#a89878', 500: '#7a6c52',
                    600: '#5a4f3a', 700: '#3f3729', 800: '#2a2419',
                    900: '#1a1611', 950: '#0d0b08',
                },
                zinc: {
                    50:  '#f7f1e3', 100: '#efe6cf', 200: '#e8dfca',
                    300: '#d6c9a8', 400: '#a89878', 500: '#7a6c52',
                    600: '#5a4f3a', 700: '#3f3729', 800: '#2a2419',
                    900: '#1a1611', 950: '#0d0b08',
                },
                // badge variants — semantic remap to Nilou palette
                // royal (was indigo) → teal family
                indigo: {
                    100: '#d8efed', 200: '#a8d8d4', 300: '#7ec5c0',
                    400: '#5bc0be', 500: '#3a9188', 600: '#2d736b',
                    700: '#244e48', 800: '#193b35', 900: '#0f2825',
                },
                // positive (was emerald) — keep green but warmer
                emerald: {
                    100: '#cdebd1', 200: '#a8d9b1', 300: '#7fc28b',
                    400: '#56a567', 500: '#358a48', 600: '#256d35',
                    700: '#1b5527', 800: '#1f5d2c', 900: '#0d3216',
                },
                // warning (was amber) → Nilou gold
                amber: {
                    100: '#f6ecd2', 200: '#efe1bf', 300: '#e3cd96',
                    400: '#d4b770', 500: '#c9a253', 600: '#a98538',
                    700: '#9b7a2c', 800: '#6e561e', 900: '#3f3214',
                },
            },
            borderRadius: {
                lg: "var(--radius)",
                md: "calc(var(--radius) - 2px)",
                sm: "calc(var(--radius) - 4px)",
            },
            keyframes: {
                "accordion-down": {
                    from: { height: "0" },
                    to: { height: "var(--radix-accordion-content-height)" },
                },
                "accordion-up": {
                    from: { height: "var(--radix-accordion-content-height)" },
                    to: { height: "0" },
                },
            },
            animation: {
                "accordion-down": "accordion-down 0.2s ease-out",
                "accordion-up": "accordion-up 0.2s ease-out",
            },
            fontFamily: {
                // AEGIS fork — Nilou Network type stack.
                // Was Lato/Ubuntu (upstream Marzneshin). Cormorant Garamond
                // is loaded via dashboard/src/nilou-theme.css @import.
                'font-body': ['Inter', 'PingFang SC', 'Hiragino Sans', 'system-ui', 'sans-serif'],
                'font-header': ['Cormorant Garamond', 'Songti SC', 'Georgia', 'serif'],
                'font-mono': ['JetBrains Mono', 'ui-monospace', 'SF Mono', 'Consolas', 'monospace'],
            }
        },
    },
    plugins: [
        nextui(),
        tailwindcssAnimate,
        tailwindcssForm,
        tailwindcssAspectRatio,
        tailwindcssTypography
    ],
}

export default config;
