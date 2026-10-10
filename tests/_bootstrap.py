"""Make the repository ``scripts`` package importable when a test file runs directly."""
import sys
from pathlib import Path

SCRIPTS = str(Path(__file__).resolve().parents[1] / 'scripts')
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)
