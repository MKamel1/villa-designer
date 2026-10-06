"""Run one of the two approved, scoped agy research jobs."""

import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path.home() / ".claude" / "jobs" / "cd6cb945" / "tmp" / "agy_work"
WORK = ROOT / "out" / "agy-research"
JOBS = {
    "garden": ("prompt_garden.txt", "garden-brief-research.md"),
    "light": ("prompt_light.txt", "lighting-upper-bounds.md"),
}
TOOL_NOTE = (
    "Use built-in view_file, grep_search, search_web, read_url_content and "
    "write_to_file tools. Do not call run_command or any shell command. "
    "The ref folder already exists in this workspace. Write only the "
    "requested Markdown output file.\n\n"
)


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in JOBS:
        print("Usage: python scripts/run_agy_research.py garden|light", file=sys.stderr)
        return 2
    prompt_name, result_name = JOBS[sys.argv[1]]
    prompt = TOOL_NOTE + (SOURCE / prompt_name).read_text(encoding="utf-8-sig")
    result_path = WORK / result_name
    if not WORK.is_dir() or not (WORK / "ref").is_dir():
        print("Research folder or reference files are missing", file=sys.stderr)
        return 2
    before = result_path.stat().st_mtime_ns if result_path.exists() else None
    completed = subprocess.run(
        ["agy", "--output-format", "json", "-p", prompt],
        cwd=WORK,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    lines = completed.stdout.splitlines()
    try:
        report = json.loads(next(line for line in reversed(lines) if line.startswith("{")))
    except (StopIteration, json.JSONDecodeError):
        print(completed.stderr[-1200:], file=sys.stderr)
        print("agy returned no parseable result", file=sys.stderr)
        return 1
    if completed.returncode or report.get("status") != "SUCCESS" or report.get("denied_actions"):
        print(completed.stderr[-1200:], file=sys.stderr)
        print(f"agy did not complete cleanly: {report.get('status')}", file=sys.stderr)
        return 1
    if not result_path.is_file() or not result_path.stat().st_size:
        print(f"agy did not write {result_path}", file=sys.stderr)
        return 1
    if before is not None and result_path.stat().st_mtime_ns == before:
        print(f"agy did not update {result_path}", file=sys.stderr)
        return 1
    print(f"Created {result_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
