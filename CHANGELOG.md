# Changelog

## 0.2.0 — 2026-10-30

- Extracted as a standalone project with a root-level GitHub Actions workflow.
- Added virtual-environment setup, synthetic example data and an offline graph preview.
- Shared CSV validation between analysis and plotting; count failed speed tests and preserve missing latency.
- Validate intervals and existing CSV headers, initialise empty files, use a predictable ping locale and monotonic scheduling.
- Removed automatic acceptance of Ookla agreements; increased default interval to 15 minutes.
- Check collector process identity, serialise wrapper commands and honour custom graph directories.
- Added offline regression tests and Python 3.9/3.11 CI checks.
