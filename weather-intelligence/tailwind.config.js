/** @type {import('tailwindcss').Config} */
export default {
  content: ["./web/index.html", "./web/src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#1E2A32",
        mist: "#D5DDE3",
        haze: "#8A9AA6",
        gulf: "#3F6F7A",
        gale: "#C4A35A",
        squall: "#B54A3C",
      },
      fontFamily: {
        phrase: ["Fraunces", "ui-serif", "Georgia", "serif"],
        ui: ["Schibsted Grotesk", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      fontSize: {
        phrase: ["2.125rem", { lineHeight: "1.15", letterSpacing: "-0.02em" }],
        temp: ["4rem", { lineHeight: "1", letterSpacing: "-0.04em" }],
      },
      transitionTimingFunction: {
        settle: "cubic-bezier(0.22, 1, 0.36, 1)",
      },
    },
  },
  plugins: [],
};
