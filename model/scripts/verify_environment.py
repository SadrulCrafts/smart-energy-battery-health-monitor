"""
verify_environment.py
---------------------
Stage 0 check: confirms that the Python environment is set up correctly.

Run from the project root (with the virtual environment activated):
    python model/scripts/verify_environment.py
"""

import importlib
import sys
from pathlib import Path

REQUIRED_PACKAGES = [
    # (import name, name shown to the user)
    ("numpy", "numpy"),
    ("pandas", "pandas"),
    ("scipy", "scipy"),
    ("matplotlib", "matplotlib"),
    ("sklearn", "scikit-learn"),
    ("joblib", "joblib"),
]

MODEL_DIR = Path(__file__).resolve().parent.parent
REQUIRED_FOLDERS = [
    MODEL_DIR / "scripts",
    MODEL_DIR / "data" / "raw",
    MODEL_DIR / "data" / "processed",
]


def main():
    all_ok = True

    print(f"Python executable : {sys.executable}")
    print(f"Python version    : {sys.version.split()[0]}")

    if sys.version_info < (3, 10):
        print("  [FAIL] Python 3.10 or newer is required.")
        all_ok = False
    else:
        print("  [OK]   Python version is supported.")

    # A virtual environment has a different sys.prefix than the base Python.
    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    if in_venv:
        print("  [OK]   Running inside a virtual environment.")
    else:
        print("  [WARN] Not inside a virtual environment. Did you activate .venv?")

    print("\nPackages:")
    for import_name, display_name in REQUIRED_PACKAGES:
        try:
            module = importlib.import_module(import_name)
            version = getattr(module, "__version__", "unknown")
            print(f"  [OK]   {display_name:<14} {version}")
        except ImportError:
            print(f"  [FAIL] {display_name:<14} not installed")
            all_ok = False

    print("\nProject folders:")
    for folder in REQUIRED_FOLDERS:
        rel = folder.relative_to(MODEL_DIR.parent)
        if folder.is_dir():
            print(f"  [OK]   {rel}")
        else:
            print(f"  [FAIL] {rel} is missing")
            all_ok = False

    print()
    if all_ok:
        print("RESULT: Environment is ready.")
    else:
        print("RESULT: Some checks failed. Fix the [FAIL] items above.")
        sys.exit(1)


if __name__ == "__main__":
    main()