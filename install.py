from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import venv
from datetime import datetime
from pathlib import Path


REPO = Path(__file__).resolve().parent
PRODUCT_HOME = Path(os.environ.get("WORK_REVIEW_PRODUCT_HOME", Path.home() / ".work-review")).expanduser().resolve()


def runtime_python(runtime: Path) -> Path:
    return runtime / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def install_runtime() -> Path:
    runtime = PRODUCT_HOME / "runtime"
    if not runtime_python(runtime).is_file():
        venv.EnvBuilder(with_pip=True).create(runtime)
    python = runtime_python(runtime)
    subprocess.run([str(python), "-m", "pip", "install", "--upgrade", str(REPO)], check=True)
    return python


def install_launchers(python: Path) -> Path:
    bin_dir = PRODUCT_HOME / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    data_home = PRODUCT_HOME / "data"
    if os.name == "nt":
        launcher = bin_dir / "work-review.cmd"
        launcher.write_text(
            f'@if not defined WORK_REVIEW_HOME set "WORK_REVIEW_HOME={data_home}"\n@"{python}" -m agent_work_review %*\n',
            encoding="utf-8",
        )
    else:
        launcher = bin_dir / "work-review"
        launcher.write_text(
            f'#!/bin/sh\n: "${{WORK_REVIEW_HOME:={data_home}}}"\nexport WORK_REVIEW_HOME\nexec "{python}" -m agent_work_review "$@"\n',
            encoding="utf-8",
        )
        launcher.chmod(0o755)
    return launcher


def replace_tree(source: Path, destination: Path) -> None:
    backup_root = PRODUCT_HOME / "backups" / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    if destination.exists():
        backup = backup_root / destination.name
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(destination, backup)
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)


def install_integrations(target: str) -> list[str]:
    source = REPO / "skills" / "agent-work-review"
    destinations = [PRODUCT_HOME / "integrations" / "agent-work-review"]
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()
    if target == "codex" or (target == "auto" and codex_home.exists()):
        destinations.append(codex_home / "skills" / "agent-work-review")
        legacy = codex_home / "skills" / "work-review-ppt-summary"
        if legacy.exists():
            replace_tree(legacy, PRODUCT_HOME / "backups" / "legacy-work-review-ppt-summary")
            shutil.rmtree(legacy)
    for destination in destinations:
        replace_tree(source, destination)
    return [str(path) for path in destinations]


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Agent Work Review into an isolated local runtime.")
    parser.add_argument("--integration", choices=["auto", "codex", "generic"], default="auto")
    args = parser.parse_args()

    PRODUCT_HOME.mkdir(parents=True, exist_ok=True)
    python = install_runtime()
    launcher = install_launchers(python)
    integrations = install_integrations(args.integration)
    runtime_env = os.environ.copy()
    runtime_env["WORK_REVIEW_HOME"] = str(PRODUCT_HOME / "data")
    subprocess.run([str(python), "-m", "agent_work_review", "init"], check=True, env=runtime_env)
    manifest = {
        "version": "1.2.0",
        "installed_at": datetime.now().astimezone().isoformat(),
        "runtime_python": str(python),
        "launcher": str(launcher),
        "integrations": integrations,
    }
    (PRODUCT_HOME / "install-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
