// Flat config. Wired at M1-0 so the C7.2 eslint job was real from Week 1; extended at FE-1
// with JSX and the two global environments this project actually has.
//
// **Two environments, on purpose.** A static export runs half its code at build time in
// Node (`app/lib/reports.js` reads the fixtures off disk) and half in a browser. Declaring
// one set of globals for everything would either hide a real `process` reference in a
// client component or flag a legitimate one in a build-time module. The split below is the
// same boundary the file tree already draws — see the note in `app/lib/labels.js`, which
// exists because a client component importing the build-time module broke the first build.
import react from "eslint-plugin-react";

export default [
  {
    files: ["**/*.{js,mjs,jsx}"],
    plugins: { react },
    languageOptions: {
      ecmaVersion: 2023,
      sourceType: "module",
      parserOptions: { ecmaFeatures: { jsx: true } },
      globals: {
        // Browser
        window: "readonly",
        document: "readonly",
        navigator: "readonly",
        fetch: "readonly",
        console: "readonly",
        localStorage: "readonly",
        sessionStorage: "readonly",
        URL: "readonly",
        Blob: "readonly",
        setTimeout: "readonly",
        clearTimeout: "readonly",
        // Added with E2's live-run panel (M3-1b). The list is an allowlist on purpose, so
        // a new browser global is a deliberate entry rather than a rule that stopped
        // noticing: `EventSource` is the SSE client, and `AbortController` bounds the
        // readiness probe so the panel cannot hang on `file://`, where there is no API.
        EventSource: "readonly",
        AbortController: "readonly",
      },
    },
    rules: {
      // Without this, every component imported and used ONLY in JSX reads as unused --
      // which is every component in the app. The base rule cannot see JSX references.
      "react/jsx-uses-vars": "error",
      "no-unused-vars": ["error", { varsIgnorePattern: "^_", argsIgnorePattern: "^_" }],
      "no-undef": "error",
      eqeqeq: "error",
    },
  },
  {
    // Build-time modules and config: Node globals, no browser.
    // Anything that reads the repo at build time. Listed by path rather than by a
    // glob over `app/lib/` so that adding a client-safe module there does not silently
    // acquire Node globals it has no business having.
    files: [
      "app/lib/reports.js",
      "app/lib/taxonomy.js",
      "app/lib/calibration.js",
      "app/lib/faithfulness.js",
      "*.config.mjs",
      "app/**/page.jsx",
      "app/**/layout.jsx",
    ],
    languageOptions: {
      globals: { process: "readonly", __dirname: "readonly", console: "readonly" },
    },
  },
  { ignores: [".next/**", "out/**", "node_modules/**"] },
];
