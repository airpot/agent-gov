#!/usr/bin/env python3
"""Package-level regression checks for agent-gov."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[2]
INIT_SCRIPT = PACKAGE_ROOT / ".codex" / "skills" / "agent-gov" / "scripts" / "init_agent_project.py"


def run(cmd: list[str], cwd: Path, expect_ok: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)
    if expect_ok and result.returncode != 0:
        print("command failed:", " ".join(cmd), file=sys.stderr)
        print(result.stdout, file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        raise SystemExit(result.returncode)
    if not expect_ok and result.returncode == 0:
        print("command unexpectedly passed:", " ".join(cmd), file=sys.stderr)
        print(result.stdout, file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        raise SystemExit(1)
    return result


def main() -> int:
    python = sys.executable
    temp_root = Path(tempfile.mkdtemp(prefix="agent-gov-regression-"))
    try:
        if sys.platform.startswith("win"):
            target = temp_root / "agent-gov"
        else:
            target = temp_root / r"C:\Users\airpot\AppData\Local\Temp\agent-gov"
        target.mkdir(parents=True, exist_ok=True)

        run(
            [
                python,
                str(INIT_SCRIPT),
                str(target),
                "--tech-stack",
                "python",
                "--layout",
                "minimal",
                "--remote-kind",
                "local",
            ],
            cwd=PACKAGE_ROOT,
        )

        config_path = target / ".agent" / "config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        if config.get("schema") != "agent-project-config-v1":
            print(".agent/config.json has the wrong schema", file=sys.stderr)
            return 1
        if "\\" in str(target) and config.get("remote_workspace_path") != str(target.resolve()):
            print(".agent/config.json did not preserve the workspace path", file=sys.stderr)
            return 1
        expected_schemas = {
            ".agent/risk-zones.json": "agent-risk-zones-v1",
            ".agent/review-policy.json": "agent-review-policy-v1",
        }
        for relative, schema in expected_schemas.items():
            path = target / relative
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("schema") != schema:
                print(f"{relative} has the wrong schema", file=sys.stderr)
                return 1
        if not (target / "docs" / "AI_CODING_GLOSSARY.md").exists():
            print("docs/AI_CODING_GLOSSARY.md was not created", file=sys.stderr)
            return 1

        run([python, "scripts/agent_check.py"], cwd=target)
        run([python, "scripts/agent_score.py", "doctor"], cwd=target)
        run([python, "scripts/agent_score.py", "score", "--write"], cwd=target)

        config_path.write_text('{"schema":"agent-project-config-v1","remote_workspace_path":"C:\\bad"\n', encoding="utf-8")
        doctor = run([python, "scripts/agent_score.py", "doctor"], cwd=target, expect_ok=False)
        score = run([python, "scripts/agent_score.py", "score", "--write"], cwd=target, expect_ok=False)
        combined_output = doctor.stdout + doctor.stderr + score.stdout + score.stderr
        if "project_integrity" not in combined_output and "invalid JSON" not in combined_output:
            print("invalid JSON was not reported as project integrity failure", file=sys.stderr)
            print(combined_output, file=sys.stderr)
            return 1

        existing = temp_root / "existing-layout"
        for directory in ("cmd", "pkg", "docs", "scripts"):
            (existing / directory).mkdir(parents=True, exist_ok=True)
        run(
            [
                python,
                str(INIT_SCRIPT),
                str(existing),
                "--layout",
                "existing",
                "--dir",
                "cmd,pkg",
                "--no-create-layout",
            ],
            cwd=PACKAGE_ROOT,
        )
        run([python, "scripts/agent_check.py"], cwd=existing)

        escaped = temp_root / "path-escape"
        escaped.mkdir(parents=True, exist_ok=True)
        escape_result = run(
            [python, str(INIT_SCRIPT), str(escaped), "--dir", "../outside"],
            cwd=PACKAGE_ROOT,
            expect_ok=False,
        )
        if "must not contain . or .." not in (escape_result.stdout + escape_result.stderr):
            print("path traversal in --dir was not rejected clearly", file=sys.stderr)
            print(escape_result.stdout, file=sys.stderr)
            print(escape_result.stderr, file=sys.stderr)
            return 1
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
