"""Thin wrapper around the vendored Vault-LD converter (write-back stays off in app flows)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "vendor" / "vault-ld-scripts"

# Product lock: Markdown is master; do not enable graph→file write-back here.
WRITE_BACK = os.environ.get("CORE_WRITE_BACK", "0") == "1"


def export_vault(vault: Path, out_dir: Path, *, source: bool = True) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, str(SCRIPTS / "vault_to_rdf.py"), str(vault), "--out-dir", str(out_dir)]
    if source:
        cmd.append("--source")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SCRIPTS) + os.pathsep + env.get("PYTHONPATH", "")
    subprocess.check_call(cmd, env=env)


def ingest_rdf(vault: Path, *rdf_files: Path, context: Path | None = None) -> None:
    if not WRITE_BACK:
        raise RuntimeError(
            "graph→file write-back is off (CORE_WRITE_BACK=0). "
            "Set CORE_WRITE_BACK=1 only when deliberately rehydrating a vault for tooling."
        )
    cmd = [sys.executable, str(SCRIPTS / "rdf_to_vault.py"), str(vault), *[str(p) for p in rdf_files]]
    if context:
        cmd.extend(["--context", str(context)])
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SCRIPTS) + os.pathsep + env.get("PYTHONPATH", "")
    subprocess.check_call(cmd, env=env)
