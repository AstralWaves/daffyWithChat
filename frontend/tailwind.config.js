/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,jsx,ts,tsx}", "./public/index.html"],
  theme: {
    extend: {
      fontFamily: {
        heading: ["'Cabinet Grotesk'", "sans-serif"],
        body: ["'Satoshi'", "sans-serif"],
      },
      colors: {
        sand: "#F9F8F6",
        sidebar: "#F0EBE1",
        terracotta: "#C85A47",
        terracottaHover: "#B34D3C",
        forest: "#38423B",
        sage: "#788A6F",
        ink: "#1C1C1A",
        muted: "#7A7A75",
        bordr: "#E5E0D8",
      },
      borderRadius: {
        bubble: "1rem",
      },
    },
  },
  plugins: [],
};
