"""journeyman: run journeys, judge them, diff them, dashboard them.

    journeyman demo                    offline, no keys needed
    journeyman run <name>              one journey, live Solari
    journeyman run --all               every journey in journeys/
    journeyman list                    show configured journeys
    journeyman serve [--directory D]   static dashboard (default: runs/)
"""

from __future__ import annotations

import argparse
import asyncio
import http.server
import os
import sys
from pathlib import Path

from .demo import run_demo
from .engine import run_live_journey
from .journeys import find_journey, load_all_journeys

ROOT = Path(__file__).resolve().parent.parent
JOURNEYS_DIR = ROOT / "journeys"
RUNS_DIR = ROOT / "runs"


def _require_api_key() -> str:
    key = os.environ.get("SOLARI_API_KEY")
    if not key:
        print("SOLARI_API_KEY is not set. Get one at console.getsolari.com and:", file=sys.stderr)
        print("  export SOLARI_API_KEY=slr_live_...", file=sys.stderr)
        raise SystemExit(1)
    return key


async def _run_all_live(journeys, runs_dir: Path) -> list[dict]:
    from solari_sandbox import SandboxClient

    from .diff import SandboxDiffer

    api_key = _require_api_key()
    records = []
    async with SandboxClient(api_key=api_key, base_url="https://api.getsolari.com") as client:
        differ = await SandboxDiffer.create(client)
        try:
            for journey in journeys:
                print(f"-> {journey.name} ({journey.backend})...", end=" ", flush=True)
                record = await run_live_journey(journey, api_key=api_key, runs_dir=runs_dir, differ=differ)
                print("PASS" if record["passed"] else "FAIL")
                records.append(record)
        finally:
            await differ.close()
    return records


def cmd_demo(args: argparse.Namespace) -> None:
    runs_dir = Path(args.directory) if args.directory else RUNS_DIR / "demo"
    records = run_demo(runs_dir)
    for r in records:
        print(f"{'PASS' if r['passed'] else 'FAIL'}  {r['journey']:<24} diff={r['diff_pct']}%  {r['run_id']}")
    print(f"\nOpen {runs_dir / 'index.html'} or run: journeyman serve --directory {runs_dir}")


def cmd_run(args: argparse.Namespace) -> None:
    runs_dir = Path(args.directory) if args.directory else RUNS_DIR
    if args.all:
        journeys = load_all_journeys(JOURNEYS_DIR)
    else:
        if not args.name:
            print("usage: journeyman run <name> | journeyman run --all", file=sys.stderr)
            raise SystemExit(2)
        journeys = [find_journey(JOURNEYS_DIR, args.name)]

    records = asyncio.run(_run_all_live(journeys, runs_dir))
    failures = [r for r in records if not r["passed"]]
    print(f"\n{len(records) - len(failures)}/{len(records)} passed.")
    if failures:
        raise SystemExit(1)


def cmd_list(_args: argparse.Namespace) -> None:
    for journey in load_all_journeys(JOURNEYS_DIR):
        print(f"{journey.name:<30} {journey.backend:<8} {journey.description}")


def cmd_serve(args: argparse.Namespace) -> None:
    directory = Path(args.directory) if args.directory else RUNS_DIR
    if not directory.exists():
        print(f"{directory} does not exist yet — run `journeyman demo` or `journeyman run --all` first.", file=sys.stderr)
        raise SystemExit(1)

    handler = lambda *a, **kw: http.server.SimpleHTTPRequestHandler(*a, directory=str(directory), **kw)
    with http.server.ThreadingHTTPServer(("127.0.0.1", args.port), handler) as httpd:
        print(f"Serving {directory} at http://127.0.0.1:{args.port}/index.html  (Ctrl+C to stop)")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="journeyman", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_demo = sub.add_parser("demo", help="run the offline demo (no keys needed)")
    p_demo.add_argument("--directory", help="where to write runs (default: runs/demo)")
    p_demo.set_defaults(func=cmd_demo)

    p_run = sub.add_parser("run", help="run one or all journeys against live Solari")
    p_run.add_argument("name", nargs="?", help="journey name (see `journeyman list`)")
    p_run.add_argument("--all", action="store_true", help="run every journey in journeys/")
    p_run.add_argument("--directory", help="where to write runs (default: runs/)")
    p_run.set_defaults(func=cmd_run)

    p_list = sub.add_parser("list", help="list configured journeys")
    p_list.set_defaults(func=cmd_list)

    p_serve = sub.add_parser("serve", help="serve a runs directory's dashboard")
    p_serve.add_argument("--directory", help="directory to serve (default: runs/)")
    p_serve.add_argument("--port", type=int, default=8787)
    p_serve.set_defaults(func=cmd_serve)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
