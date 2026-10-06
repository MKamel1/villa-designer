"""Record a checked context; exit 2 before work when the context is invalid."""
from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from archpipe.execution_context import ContextError, Tool, preflight, project_path, write_record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--script", type=Path, action="append", default=[])
    parser.add_argument("--input", type=Path, action="append", default=[])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--temp", type=Path, required=True)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--tool", nargs=3, action="append", default=[],
                        metavar=("NAME", "PATH", "EXACT_VERSION"))
    args = parser.parse_args()
    try:
        context = preflight(root=args.root, scripts=args.script, inputs=args.input, output=args.out,
                            temp=args.temp, tools=[Tool(n, Path(p), v) for n, p, v in args.tool])
        write_record(context, project_path(Path(context["working_directory"]), args.record, "context record"))
    except ContextError as exc:
        print("PREFLIGHT FAILED: " + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
