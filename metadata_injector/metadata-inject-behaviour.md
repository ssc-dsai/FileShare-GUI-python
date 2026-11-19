# Metadata inject behaviour

## What happens

1. Read each `*.metadata.json` from `PLACEHOLDERS_DIR`.
2. Locate the original file (`original_path` in JSON, otherwise search).
3. Clone it under `INJECTED_METADATA_DIR` (keeps subfolders when possible).
4. For Word/Excel files: inject **Title**, **Subject**, **Keywords**, and key custom properties (if `pywin32` is available).
5. Always write a full `.metadata.json` next to the clone.