# Contributing to FileShare-GUI

Thank you for your interest in contributing to FileShare-GUI, a local
records-management tool for the Government of Canada.

## Getting Started

1. Fork the repository and clone it into a user-writable folder (not
   `Program Files`).

   ```
   git clone https://github.com/<your-fork>/FileShare-GUI-python.git
   ```

2. Create a virtual environment and install dependencies:

   ```
   python -m venv .venv
   # activate .venv
   python -m pip install -r requirements.txt
   ```

3. Edit the absolute paths in `project_config.py` to point at your
   local source documents, extracted-texts folder, results folder,
   model folder, and resources folder.

4. Run the application:

   ```
   python app.py
   ```

   Then open `http://127.0.0.1:7860`.

## Development Workflow

- Create a feature branch from `main`: `git checkout -b my-branch`
- Keep commits small and focused; write clear commit messages.
- Follow the existing code style (PEP 8, type hints where practical).
- All pipeline phases are separate scripts launched via
  `backend/runners.py`; keep that boundary intact.
- Paths are configured **only** in `project_config.py` — do not
  hard-code absolute paths in other modules.

## Testing

There is no automated test suite. Before submitting a change, manually
run the affected pipeline phase(s) from the Gradio UI and verify:

- The phase completes without errors.
- The output files (Excel, JSON, logs) are correct.
- The Dashboard "Refresh status" counts reflect the new state.

## Code Style

- Use `pathlib.Path` for all file operations.
- Log with the `logging` module; use `logger.info` for progress and
  `logger.error` / `logger.warning` for issues.
- Sanitize strings before writing to Excel (strip illegal XML
  characters).
- Keep functions small; extract helpers when a function exceeds ~50
  lines.

## License

By submitting a pull request, you agree that your contribution will be
licensed under the MIT License, consistent with the rest of the
project. See [LICENSE](LICENSE).

## Questions

Open an issue on the GitHub repository or contact the project
maintainers.
