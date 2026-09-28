/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        canvas: "#F7F7F4",
        surface: "#FFFFFF",
        "surface-sunken": "#F0F0EB",
        ink: "#14161C",
        "ink-muted": "#565B66",
        "ink-faint": "#8B909B",
        hairline: "#E7E6DF",
        "hairline-strong": "#D9D8CF",
        brand: "#1B2E4E",
        "brand-soft": "#24406E",
        "brand-wash": "#EAF0F8",
        accent: "#2563EB",
        rise: "#B23A2E",
        "rise-wash": "#FDF2F1",
        fall: "#0E7C6B",
        "fall-wash": "#EAF6F4",
        baseline: "#9AA0AC",
        synth: "#9A5B08",
        "synth-border": "#DDAA66",
        "synth-wash": "#FEF7ED",
      },
      fontSize: {
        "hero-num": ["3.5rem", { lineHeight: "1", letterSpacing: "-0.02em" }],
        "stat-num": ["1.5rem", { lineHeight: "1.2", letterSpacing: "-0.01em" }],
      },
      borderRadius: {
        panel: "0.5rem",
      },
      boxShadow: {
        panel: "0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03)",
        "panel-hover": "0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -2px rgba(0, 0, 0, 0.04)",
      }
    },
  },
  plugins: [],
}
