# Validation record

Initial validation was performed in a Linux environment with Python 3.12 and Node available for JavaScript syntax checking.

## Passed

- Python compile check for the application and modules.
- `node --check web/app.js`.
- Python unittest suite: **29 tests passed**. See the exact test names and independently calculated examples in `tests/`.
- Local HTTP server startup and real HTTP requests for bootstrap, analysis, scenario cases, save/load, CSV/HTML/JSON exports, invalid input handling and CSRF/origin protections (automated in the suite).
- Optional AI adapter with mocked success/error responses; consent and configuration gates verified. No paid live API call was made.

## Not completed in this environment

- End-to-end visual/browser automation: Playwright was present but its Chromium executable was absent. Browser download returned an unavailable-site response. No UI screenshot or complete browser pass is claimed.
- A Windows desktop run; the launcher and Windows CI job are provided, but neither is presented as already verified on a real Windows machine.
- GitHub Actions execution or public hosting. Source publication is separate from a live deployment.
- A live OpenAI response using the owner's account/model.

## Manual browser acceptance check

Start `python app.py --open`, then verify:

1. The default dashboard shows suppliers, costs, eligibility and a recommendation.
2. Change deadline to 1 day; run comparison; check **No award recommended**.
3. Restore deadline to 21 days; edit a supplier price; confirm updated cost.
4. Set weights to an invalid total; verify a useful error without overwriting the last valid result.
5. Switch SKU; ensure only that product's offers are compared.
6. Add a quote, then remove it; do not delete saved decisions.
7. Import the sample CSV; validate replacement confirmation and product options.
8. Save a decision; open Saved decisions; load it and compare its inputs.
9. Run the Scenario lab; verify six cases and changed-winner indicators.
10. Download CSV, JSON and the printable HTML report; inspect their values.
11. Check narrow/mobile width, keyboard navigation and 200% zoom for usable controls.
12. If AI is configured, first verify no request without consent, then make one explicitly authorized request and compare its text against the deterministic figures.

An optional Playwright smoke-test script is included at `scripts/browser_smoke.cjs`. Install Playwright in a separate development environment, run the server, and invoke the script. It is not a runtime dependency of the application. The script uses a separate test database when you follow its command below, so it does not modify your decision records.

```bash
# Terminal 1 (macOS / Linux)
PROCUREMENT_DB=/tmp/procurement-browser-test.sqlite3 python app.py
# Terminal 2, in an environment that already provides Playwright and Chromium
node scripts/browser_smoke.cjs
```

On PowerShell, set `$env:PROCUREMENT_DB` to a temporary path first, then start the server. The script edits current demo state and adds a QA snapshot. Remove the temporary database after stopping the test server.
