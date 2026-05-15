/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#102a3a",
        baltic: "#005A83",
        gold: "#FFBF00",
        magenta: "#E83F6F",
        sea: "#32936F",
        skyline: "#005A83",
        coral: "#E83F6F",
        sky: {
          50: "#edf8fc",
          100: "#d6eef6",
          200: "#b4ddea",
          300: "#7bbdd4",
          600: "#005A83",
          700: "#005A83",
          800: "#00496b",
          900: "#00364f",
        },
        blue: {
          50: "#edf8fc",
          100: "#d6eef6",
          200: "#b4ddea",
          700: "#005A83",
        },
        emerald: {
          50: "#eef8f4",
          100: "#d8efe5",
          200: "#b8ddcc",
          600: "#32936F",
          700: "#2a7c5d",
          900: "#1f5d46",
        },
        teal: {
          800: "#2a7c5d",
        },
        amber: {
          50: "#fff8df",
          100: "#ffefb5",
          200: "#ffe17a",
          700: "#8a6400",
          800: "#6f5000",
        },
        yellow: {
          50: "#fff8df",
          700: "#8a6400",
        },
        rose: {
          50: "#fdeaf0",
          100: "#fbd0dd",
          200: "#f7a8bf",
          700: "#b71f4c",
          900: "#8f183b",
        },
        red: {
          50: "#fdeaf0",
          200: "#f7a8bf",
          700: "#b71f4c",
        },
        indigo: {
          50: "#edf8fc",
          200: "#b4ddea",
          700: "#005A83",
        },
        orange: {
          50: "#fff8df",
        },
      },
      boxShadow: {
        soft: "0 12px 30px rgba(15, 23, 42, 0.08)",
      },
    },
  },
  plugins: [],
};
