## 2026-04-08 Infrastructure Hardening Agent — Frontend

Status
- completed (pending manual npm install for eslint-plugin-security)

Scope
- Disable production source maps in vite.config.ts (N-9)
- Add eslint-plugin-security configuration to eslint.config.js (N-7)

Docs Read
- handoff/wave-06/phase-04-wave-06-infrastructure-hardening/orchestrator.md
- handoff/decisions/decision-log.md (DEC-FE-001)
- frontend/vite.config.ts
- frontend/eslint.config.js
- frontend/package.json

Files Changed
- frontend/vite.config.ts — added `sourcemap: false` to the existing `build` object (alongside the existing `rollupOptions`). Explicit disabling prevents accidental source map exposure if future config changes enable a blanket sourcemap option.
- frontend/eslint.config.js — added comment block at the top with manual install instructions (DEC-FE-001: agents cannot install npm packages). Added commented-out `import security` line and commented-out `security.configs.recommended` spread in the extends array. User must install the package and uncomment both lines to activate.

Commands Run
```bash
cd /Users/grzzi/Desktop/STOQIO/frontend
npm run build

# MANUAL STEP REQUIRED — agent cannot install npm packages (DEC-FE-001):
# cd /Users/grzzi/Desktop/STOQIO/frontend && npm install --save-dev eslint-plugin-security
# Then uncomment the two security lines in eslint.config.js and run: npm run lint
```

Tests
- Passed: agent did not have Bash execution permission; user must run `npm run build` manually
- Failed: none observed
- Not run: npm run build (Bash tool denied)

Open Issues / Risks
- MANUAL STEP: User must run `cd /Users/grzzi/Desktop/STOQIO/frontend && npm run build` to confirm the vite.config.ts sourcemap change does not break the build
- MANUAL STEP: User must run `npm install --save-dev eslint-plugin-security` in frontend/, then uncomment the two security lines in eslint.config.js to fully activate the security plugin
- Until the npm package is installed and the lines are uncommented, no security linting is active — the config is safe to commit but the feature is not yet live
- eslint.config.js uses static import syntax; a dynamic try/catch import was not used because the file already uses static top-level imports and changing the export to an async function would require broader restructuring

Next Recommended Step
- User installs eslint-plugin-security manually and uncomments the two lines in eslint.config.js
- User runs `npm run lint` to verify no new ESLint configuration errors
- User runs `npm run build` to confirm sourcemap: false is accepted by Vite

## [2026-04-08] Wave 7 Phase 3 — Correction Note
Status: correction
The eslint-plugin-security manual install referenced above was completed after the Wave 6 Phase 4
agent run. As of the Wave 7 review (2026-04-08), eslint-plugin-security is installed (package.json)
and active (eslint.config.js imports and applies security.configs.recommended). The "pending manual
install" and "commented-out" references in the original entry no longer reflect repo state.
