// Security plugin — install manually before enabling (DEC-FE-001):
//   cd /Users/grzzi/Desktop/STOQIO/frontend && npm install --save-dev eslint-plugin-security
// Then uncomment the import and the spread below:
// import security from 'eslint-plugin-security'

import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
      // security.configs.recommended,  // uncomment after npm install --save-dev eslint-plugin-security
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
  },
])
