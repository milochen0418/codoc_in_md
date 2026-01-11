# E2E testcases

This folder contains Playwright end-to-end suites.

## Structure

Each suite lives under:

- `testcases/<suite_name>/run_test.py`
- `testcases/<suite_name>/output/` (artifacts, ignored by git)

The `run_test.py` script should:
- Exit `0` on success
- Exit non-zero on failure
- Write screenshots/logs into `OUTPUT_DIR` (provided by the runner)

## Running

Use the repo-level runner (it manages starting/stopping the Reflex server and collecting artifacts):

```bash
poetry run ./run_test_suite.sh smoke_home
```

Optional env vars:
- `BASE_URL` (default `http://127.0.0.1:3000`)
- `HEADLESS=0` to watch the browser
