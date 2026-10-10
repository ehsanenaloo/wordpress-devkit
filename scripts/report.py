"""Render a validated DevKit evidence JSON report, optionally compared with a prior run."""
from pathlib import Path
import runpy
import sys

DIRECTORY = Path(__file__).resolve().parents[1] / 'src/skills/wp-devkit-site-audit-and-onboarding/scripts'
sys.path.insert(0, str(DIRECTORY))
if __name__ == '__main__':
    runpy.run_path(str(DIRECTORY / 'evidence_report.py'), run_name='__main__')
