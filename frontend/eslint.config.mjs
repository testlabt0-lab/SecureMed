/**
 * ESLint configuration (flat config, ESLint 9).
 *
 * package.json advertised `"lint": "eslint src --ext ts,tsx"` while the repository
 * carried no config file and no eslint packages at all, so the script failed on
 * every invocation — and `src/components/AIAssistant.tsx` had an
 * `eslint-disable-line react-hooks/exhaustive-deps` directive pointing at a rule
 * that was never installed. Both are fixed together: without a working linter the
 * disable comment was documentation, not suppression.
 *
 * Two file-level details that are easy to get wrong here:
 *  - This is `.mjs`, not `.js`. package.json has no `"type": "module"` (see
 *    postcss.config.js and tailwind.config.js, which are CommonJS), so a bare
 *    `eslint.config.js` would be loaded as CommonJS and the imports below would
 *    throw at startup.
 *  - The `--ext` flag was removed in ESLint 9. File selection now comes from the
 *    `files` patterns in this config, which is why the npm script is plain
 *    `eslint src`.
 */
import js from '@eslint/js';
import globals from 'globals';
import tseslint from 'typescript-eslint';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';

export default tseslint.config(
  {
    ignores: ['dist', 'build', 'coverage', 'node_modules'],
  },
  {
    files: ['src/**/*.{ts,tsx}'],
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      // Browser only. Nothing under src/ runs in Node — the Vite config and the
      // PostCSS/Tailwind configs are excluded by the `files` pattern above.
      globals: globals.browser,
    },
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      // ─── Correctness: these catch real bugs, so they fail the build ─────────
      ...reactHooks.configs.recommended.rules,

      // ─── Deliberately relaxed ───────────────────────────────────────────────
      //
      // `any` appears 257 times across 40 files under src/ — every API payload is
      // typed `any` because there are no generated types for the DRF serializers.
      // Leaving this rule at its `recommended` severity (error) would produce 257
      // failures on a clean checkout, which is the reliable way to get a lint
      // script ignored forever. Typing the api/ layer against the serializers is
      // worth doing, but it is its own task; this rule should be switched back on
      // as the last step of that work, not before it.
      '@typescript-eslint/no-explicit-any': 'off',

      // Warn, not error: the codebase has genuine leftovers (unused imports after
      // refactors) that are worth surfacing, but tsconfig.json sets
      // `noUnusedLocals: false`, so this rule is the only thing that sees them and
      // a hard failure on day one would block unrelated work. `_`-prefixed names
      // are the conventional opt-out for a deliberately unused binding.
      '@typescript-eslint/no-unused-vars': [
        'warn',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_', caughtErrorsIgnorePattern: '^_' },
      ],

      // ─── Project-specific ───────────────────────────────────────────────────
      //
      // `console.warn`/`console.error` are allowed: ErrorBoundary, the axios
      // interceptor and the device/MFA screens use them as real diagnostics.
      // `console.log` is not, and the reason is specific to this product rather
      // than style — anything logged from these screens is patient data sitting in
      // the browser console of a shared clinical workstation. Today only the two
      // WebSocket connection messages in hooks/useRealtimeNotifications.ts trip
      // this, and neither prints a payload; the rule exists to keep it that way.
      'no-console': ['warn', { allow: ['warn', 'error'] }],

      // A stray `==` against a role code or an id is the kind of comparison that
      // silently succeeds on a type coercion nobody intended.
      eqeqeq: ['warn', 'smart'],

      // Fast-refresh only works when a module's exports are all components. This
      // is advisory because several pages legitimately export a helper alongside
      // the default component.
      'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],
    },
  },
);
