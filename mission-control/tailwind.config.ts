import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        obsidian: {
          base: "#0D1117",
          container: "#161B22",
          border: "#30363D",
          hover: "#21262D",
          muted: "#8B949E",
          light: "#C9D1D9",
          bright: "#F0F6FC",
        },
        telemetry: {
          nominal: "#10B981",    // Emerald Green
          nominalGlow: "#059669",
          breach: "#EF4444",     // Pulsing Red
          breachGlow: "#DC2626",
          inhibited: "#F59E0B",  // Amber Warning
          inhibitedGlow: "#D97706",
          recovered: "#06B6D4",  // Cyan
          recoveredGlow: "#0891B2",
          accent: "#38BDF8",     // Sky Blue
          purple: "#A855F7",
        },
      },
      fontFamily: {
        mono: [
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Monaco",
          "Consolas",
          "Liberation Mono",
          "Courier New",
          "monospace",
        ],
      },
      animation: {
        "pulse-fast": "pulse 1s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "ping-slow": "ping 2s cubic-bezier(0, 0, 0.2, 1) infinite",
        "glitch": "glitch 0.4s ease-in-out infinite alternate",
        "radar-sweep": "radar 4s linear infinite",
      },
      keyframes: {
        glitch: {
          "0%": { transform: "translate(0px, 0px)" },
          "20%": { transform: "translate(-2px, 1px)" },
          "40%": { transform: "translate(2px, -1px)" },
          "60%": { transform: "translate(-1px, 2px)" },
          "80%": { transform: "translate(1px, -2px)" },
          "100%": { transform: "translate(0px, 0px)" },
        },
        radar: {
          "0%": { transform: "rotate(0deg)" },
          "100%": { transform: "rotate(360deg)" },
        },
      },
    },
  },
  plugins: [],
};
export default config;
