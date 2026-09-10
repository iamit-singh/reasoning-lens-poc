// Flat config, no framework plugins yet -- the Next.js config lands with the frontend
// in W5. Wired now so the C7.2 eslint job is real from Week 1.
export default [
  {
    files: ["**/*.{js,mjs,jsx,ts,tsx}"],
    languageOptions: { ecmaVersion: 2023, sourceType: "module" },
    rules: {
      "no-unused-vars": "error",
      "no-undef": "error",
      eqeqeq: "error",
    },
  },
];
