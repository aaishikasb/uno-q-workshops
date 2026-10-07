# Workshop monorepo

## Select the workshop

- Before editing, resolve the requested workshop number or name using the [root README](./README.md), then read that workshop's README. If the target cannot be determined from the request or current context, ask which workshop.
- Scope searches and edits to the selected `<number>-<name>/` folder. Include the workshop folder in file references, for example `101-haptic-dial/workshop-app/python/main.py`.
- Each workshop is an independent Arduino App Lab project. Its `workshop-app/` is the editable source; its sibling `workshop-app.zip` is the import artifact. Keep Python, sketch, and app configuration from the same workshop together. When changing packaged source, refresh that workshop's ZIP while preserving its archive layout.
- Use the root README for the workshop catalog and series descriptions; use each workshop's README for its setup and behavior. Catalog requests target the root README.
- Keep 10x workshops under hardware and App Lab foundations and 20x workshops under on-device machine learning in the catalog. Preserve the existing numbered folder paths.

## Verify changes

- App Lab compiles and runs each project; there is no repository-wide package manager or build command. Read the selected workshop's configuration and README for its dependencies and hardware requirements.
- For documentation changes, check relative links and run `git diff --check`.
- For code changes, run the selected workshop's available regression check from the repository root:
  - 104: `python3 -B 104-safe-cracker/test_safe_cracker.py`
  - 202: `python3 -B 202-anomaly-dial/test_anomaly_dial.py`
- For nontrivial logic without a check, add one small runnable regression check in that workshop. Report App Lab import, board compilation, and physical behavior as unverified unless tested on the UNO Q.
