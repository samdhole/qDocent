import os
import runpy
import sys
from pathlib import Path


def test_eval_ragas_script_imports_when_executed_by_path(monkeypatch) -> None:
    root = Path.cwd()
    scripts_dir = root / "scripts"
    filtered_path = [
        entry
        for entry in sys.path
        if entry not in ("", str(root), os.getcwd())
    ]
    monkeypatch.setattr(sys, "path", [str(scripts_dir), *filtered_path])

    runpy.run_path(str(scripts_dir / "eval_ragas.py"), run_name="__not_main__")
