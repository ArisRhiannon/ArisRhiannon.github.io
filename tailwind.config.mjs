/** @type {import('tailwindcss').Config} */
export default {
	content: ['./src/**/*.{astro,html,js,jsx,md,mdx,svelte,ts,tsx,vue}'],
	theme: {
		extend: {
			fontFamily: {
				sans: ['Inter', 'sans-serif'],
				serif: ['"EB Garamond"', 'serif'],
				display: ['Cinzel', 'serif'],
				mono: ['"JetBrains Mono"', 'monospace'],
			}
		},
	},
	plugins: [],
}
