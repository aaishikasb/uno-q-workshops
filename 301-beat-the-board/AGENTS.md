# Beat the Board

- Run commands from the repository root. Use a Python 3.12/3.13 virtual environment with `301-beat-the-board/training/requirements.txt` for model work; the game regression check uses the standard library and a C++17 compiler for its MCU simulation.
- Run `python3 -B 301-beat-the-board/test_beat_the_board.py` after changing game, Bridge, or sketch behavior.
- For model/export changes, run `training/train.py` only when retraining is needed, then `training/export.py` and `workshop-app/python/check_runtime.py` with the workshop environment. All paths are under `301-beat-the-board/`.
- After editing packaged source or model files, run `python3 -B 301-beat-the-board/package.py` to refresh and verify the ZIP.
- Keep [README.md](./README.md) focused on participant setup and gameplay.
