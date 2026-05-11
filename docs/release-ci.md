# Release CI

Newton release branches and tags must keep three required GitHub checks green:

- `fast-tests`: unit and artifact-contract tests without browser installation.
- `browser-tests`: Playwright-backed web integration and dogfood evidence tests.
- `package-smoke`: build sdist/wheel, install the built wheel in a clean environment, and smoke the installed `newton` CLI.

Branch protection for `main`, `release/**`, and `v*` release tags should require all three checks before publishing a release. Browser failures upload Playwright traces and screenshots when available so release failures can be inspected without rerunning the job immediately.
