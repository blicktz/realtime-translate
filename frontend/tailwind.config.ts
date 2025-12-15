import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  // In Tailwind v4, theme configuration is moved to CSS using @theme directive
  // See app/globals.css for custom colors, fonts, and other theme values
}

export default config
