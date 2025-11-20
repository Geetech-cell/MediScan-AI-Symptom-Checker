# Contributing to MediScan

Thanks for your interest in contributing! This project is intended for prototypes and demonstration of an AI symptom checker. Contributions are welcome — especially for:

- Expanding the `DISEASE_INFO` entries with curated descriptions, advice, and keywords
- Improving the mock server mappings and heuristics
- Adding model training / serialization scripts for production use
- UI improvements, accessibility, and documentation updates

Please follow these guidelines:

1. Fork the repository and create a feature branch: `git checkout -b feat/my-change`
2. Run tests locally and ensure they pass: `python -m pytest -q`
3. Open a pull request describing the change and linking any issues.

Coding style
- Keep code simple and readable.
- Use meaningful variable names and avoid unnecessary complexity.
- Follow existing code style; format Python with `black` if adding large patches.

Tests
- Add tests for any logic changes (see `tests/` directory)
- Ensure new tests run under pytest locally

Thanks — your contributions help improve the project for everyone.
