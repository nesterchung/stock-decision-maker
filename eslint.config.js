// Resolve @eslint/js from the Node validator's local node_modules to avoid
// polluting the repo root with JS dev dependencies.
const js = require(require.resolve("@eslint/js", {
  paths: [__dirname + "/src/node_validator/node_modules"],
}));

module.exports = [
  {
    ignores: ["**/node_modules/**"],
  },
  js.configs.recommended,
  {
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "commonjs",
      globals: {
        console: "readonly",
        process: "readonly",
      },
    },
    rules: {
      // Keep linting focused on correctness; allow unused prefixed args.
      "no-unused-vars": ["error", { argsIgnorePattern: "^_", caughtErrors: "all", caughtErrorsIgnorePattern: "^_" }],
    },
  },
];

