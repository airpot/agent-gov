# Frontend Web Governance

Use this reference when a target project has a browser-facing Web application, a `web-app` layout, explicit frontend intake, or an existing frontend package manifest.

## Contents

- [Activation And Authority](#activation-and-authority)
- [Stack Selection](#stack-selection)
- [Implementation Contract](#implementation-contract)
- [Harness And Browser Evidence](#harness-and-browser-evidence)
- [Accessibility And Performance](#accessibility-and-performance)
- [Apache ECharts](#apache-echarts)
- [Security](#security)
- [Review And Release](#review-and-release)
- [Official Sources](#official-sources)

## Activation And Authority

- Enable the `frontend-web` extension for `--layout web-app`, explicit frontend architecture intake, or detected frontend framework dependencies in an existing `package.json`.
- Keep it absent from non-Web projects. Do not add frontend paths, score dimensions, commands, or release gates to backend-only scaffolds.
- Use `.agent/blueprint.json#/frontend_stack_decision` for the cross-feature architecture summary.
- Use `.agent/frontend.json` for detailed stack, visualization, accessibility, performance, security, harness-lane, and rendered-evidence policy.
- Run `python3 scripts/agent_frontend.py doctor`, then `readiness` before frontend implementation or release claims. Use `report --json` for review evidence.
- Preserve the existing frontend framework, package manager, dependency versions, and lockfile. Never migrate or install application dependencies during agent-gov initialization.

## Stack Selection

For a greenfield client-rendered application, recommend:

- React
- TypeScript with strict mode
- Vite
- React Router

Treat this as the client application profile, not a universal rule for every React product. Select Next.js when the requirements explicitly need one or more of:

- search-engine-indexable server output;
- SSR or SSG;
- streaming server rendering;
- React Server Components;
- an integrated React server runtime, route handlers, or server actions;
- a reviewed deployment/platform requirement that is best served by Next.js.

Record the normalized qualifying requirement and deployment boundary. A non-standard reason is acceptable only through `nextjs_reviewed_exception` with a non-empty rationale, owner, and existing repository-relative review-evidence file. An arbitrary rationale or unknown qualifier does not confirm Next.js. Do not select Next.js merely because React is present.

For an existing project, prefer manifest and lockfile evidence over defaults. Preserve Vue, Angular, Svelte, Solid, React, Next.js, or another detected stack and record ambiguous choices as open decisions. Use lockfile-first version policy and do not guess package pins.

## Implementation Contract

- Keep components small enough to test and reuse; colocate only application-owned code that follows the current repository pattern.
- Record client/server boundaries, state ownership, data fetching, routing, form validation, error boundaries, authentication state, and cache policy when they affect behavior.
- Require stable dimensions and responsive constraints for boards, charts, grids, toolbars, canvases, and other fixed-format interactive elements.
- Implement loading, empty, partial, error, and success states for every remote or asynchronous surface.
- Verify supported mobile and desktop viewports. Text, controls, overlays, menus, dialogs, sticky regions, and visualizations must not overlap or escape their containers.
- Preserve keyboard interaction, focus visibility and restoration, semantic landmarks, labels, accessible names, reduced-motion behavior, and non-pointer operation.
- Keep browser console errors, unhandled promise rejections, hydration errors, and broken asset requests at zero for acceptance paths unless a reviewed exception records residual risk.

## Harness And Browser Evidence

Define these lanes in `.agent/frontend.json#/harness/lanes`:

- `frontend_static`: formatting, lint, typecheck, and production build prechecks.
- `frontend_component`: component behavior and isolated-state checks.
- `frontend_e2e`: browser-driven critical user journeys.
- `frontend_visual`: rendered viewport or component visual comparisons.
- `frontend_a11y`: automated accessibility checks plus recorded manual interaction coverage.
- `frontend_performance`: bundle and/or runtime performance evidence.
- `frontend_security`: frontend dependency and untrusted-content boundaries.
- `frontend_release`: final aggregation gate.

Commands are application-owned. Agent-gov does not install Playwright, Storybook, axe, Lighthouse, browsers, or related packages. `doctor` validates the policy even when optional tools are missing. `readiness` requires a command and repository-relative evidence path for each lane marked `required`.

Run configured lanes through `python3 scripts/agent_frontend.py run-lane <lane>`. The runner executes the exact configured command and atomically records lane, command, unpredictable run id, timestamps, exit code, status, and producer under the configured evidence path. A hand-written pass flag, empty file, missing path, stale record, or evidence for a different command does not satisfy readiness.

Run the browser acceptance command through `python3 scripts/agent_frontend.py run-browser`. The runner exposes `AGENT_FRONTEND_RUN_ID`, `AGENT_FRONTEND_EVIDENCE_PATH`, `AGENT_FRONTEND_STARTED_AT`, `AGENT_FRONTEND_VIEWPORTS_JSON`, and `AGENT_FRONTEND_BROWSER_FAMILIES_JSON` to the application-owned command. That command must write an `agent-frontend-browser-evidence-v1` record with the provided run id, browser-rendered pass status, covered viewports and browser families, interaction/responsive/accessibility results, and zero console, rejection, and failed-request counts. The runner writes a sidecar receipt that binds the exact command, run id, execution window, path, exit code, and evidence SHA-256.

Final frontend acceptance requires a real browser to render the application. Source review, lint, typecheck, build output, DOM string inspection, static HTML parsing, or screenshots created without a browser are prechecks only. A screenshot alone does not prove interaction, accessibility, responsive behavior, or runtime correctness. The runner correlation improves provenance and rejects stale or config-only assertions, but project-owned commands and files are not a cryptographic trust root or proof of reviewer identity.

## Accessibility And Performance

- Use WCAG 2.2 as the normative accessibility baseline selected by the project. Default to level AA unless the project records another reviewed target.
- Combine automated checks with keyboard, focus, zoom/reflow, screen-reader-oriented semantics, reduced-motion, and interaction review. Automated tools do not prove conformance.
- Do not use color as the only encoding. Provide labels, shapes, patterns, text, or table alternatives where meaning would otherwise be lost.
- Keep target viewports and browser families explicit. Assess mobile and desktop separately when behavior or performance differs.
- When field-oriented Core Web Vitals are enabled, use the current good thresholds at p75 as defaults: LCP at most 2.5 seconds, INP at most 200 milliseconds, and CLS at most 0.1. A specialized application may use different numeric thresholds only with `threshold_policy: reviewed-alternative` and an `alternative_policy` that records a non-empty rationale, owner, and existing repository-relative review-evidence path.
- Treat synthetic lab data and field data as different evidence. Do not claim field performance from a single local run.

## Apache ECharts

Recommend Apache ECharts only when data visualization is enabled. Keep it absent from required dependencies and release conditions otherwise. Preserve an existing visualization engine unless the user approves migration.

When ECharts is selected:

- Import `echarts/core` and only the charts, components, features, and renderer used by the application. Preserve tree-shaking; do not default to the monolithic package import.
- Give each chart container a stable, non-zero size before `init`.
- Observe container changes and call `resize()`; window resize alone may miss layout-only changes.
- Call `dispose()` during unmount or before replacing the container. Avoid duplicate chart instances and leaked listeners.
- Default to the SVG renderer for accessibility-oriented, lower-memory, and ordinary dashboard use. Select Canvas for measured large-data or effect-heavy workloads and record an existing repository-relative evidence path.
- Import/register `AriaComponent` and explicitly enable `aria` when ARIA output is required; configuration without registration is not evidence.
- Provide a nearby text summary or data table for material information. Do not rely on generated ARIA text or color alone.
- Implement loading, empty, partial, error, and success states outside or alongside the chart surface.
- Treat tooltip formatters, rich HTML, URLs, CSS-like values, callbacks, regular expressions, and data-derived markup as untrusted input boundaries. Escape or constrain them according to provenance.
- Record whether SSR/export is required. Use the ECharts server-rendering contract deliberately and verify hydration, event attachment, fonts, themes, dimensions, and export output in the selected runtime.

## Security

- Never inject untrusted values through `dangerouslySetInnerHTML`, raw tooltip HTML, URL-bearing style properties, or scriptable chart callbacks without reviewed sanitization and allowlists.
- Keep authentication tokens and private secrets out of browser bundles, HTML, source maps, frontend logs, screenshots, and tracked evidence.
- Review dependency provenance and lockfile changes. Do not run install commands from generated governance.
- Define CSP, trusted origins, navigation targets, file upload/download, cross-window messaging, storage, and third-party script boundaries when applicable.
- Treat regexes and user-controlled render loops as denial-of-service surfaces for large or adversarial data.

## Review And Release

- Review the selected stack against requirements and existing lockfiles.
- Verify every critical workflow in a real browser at supported viewports.
- Check loading, empty, partial, error, and success states; keyboard and focus behavior; accessibility; runtime errors; visual regressions; performance; and untrusted-data handling.
- For ECharts, verify container size, resize, disposal, renderer rationale, ARIA registration, alternative representation, all data states, security boundaries, and SSR/export policy.
- Require current `frontend_release` evidence before handoff, merge, or release claims. Record missing optional tooling as a limitation; never convert it into fabricated passing evidence.

## Official Sources

- React application guidance: https://react.dev/learn/creating-a-react-app
- Next.js rendering philosophy: https://nextjs.org/docs/app/guides/rendering-philosophy
- Vite guide: https://vite.dev/guide/
- WCAG 2.2: https://www.w3.org/TR/WCAG22/
- Playwright visual comparisons: https://playwright.dev/docs/test-snapshots
- Playwright accessibility testing: https://playwright.dev/docs/accessibility-testing
- Web Vitals: https://web.dev/articles/vitals
- ECharts ARIA: https://echarts.apache.org/handbook/en/best-practices/aria/
- ECharts Canvas versus SVG: https://echarts.apache.org/handbook/en/best-practices/canvas-vs-svg/
- ECharts chart size: https://echarts.apache.org/handbook/en/concepts/chart-size/
- ECharts security: https://echarts.apache.org/handbook/en/best-practices/security/
- ECharts server rendering: https://echarts.apache.org/handbook/en/how-to/cross-platform/server/

Treat these as verified source evidence for current defaults. The target repository's requirements, lockfiles, Blueprint, and reviewed exceptions remain authoritative.
