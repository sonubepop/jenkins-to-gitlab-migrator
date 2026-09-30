"""Command line interface.

    python -m jenkins2gitlab Jenkinsfile                 # print .gitlab-ci.yml
    python -m jenkins2gitlab Jenkinsfile -o .gitlab-ci.yml --report report.md
    python -m jenkins2gitlab Jenkinsfile --strict        # exit 2 if manual work is needed
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .converter import convert
from .parser import ParseError


def build_report(src_name: str, result) -> str:
    lines = [f"# Migration report for `{src_name}`", ""]
    manual = result.manual_items
    auto = [f for f in result.findings if f.level == "info"]
    lines.append(f"- Stages: {len(result.config.get('stages', []))}")
    lines.append(f"- Jobs: {len([k for k, v in result.config.items() if isinstance(v, dict) and 'script' in v])}")
    lines.append(f"- Converted automatically: {len(auto)}")
    lines.append(f"- Need manual review: {len(manual)}")
    lines.append("")
    if manual:
        lines.append("## Manual review")
        lines.append("")
        lines.extend(f"- [ ] **{f.where}**: {f.message}" for f in manual)
        lines.append("")
    lines.append("## Automatic conversions")
    lines.append("")
    lines.extend(f"- {f.where}: {f.message}" for f in auto)
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="jenkins2gitlab", description="Convert a declarative Jenkinsfile to .gitlab-ci.yml")
    ap.add_argument("jenkinsfile", help="path to the Jenkinsfile ('-' for stdin)")
    ap.add_argument("-o", "--output", help="write .gitlab-ci.yml here instead of stdout")
    ap.add_argument("--report", help="write a Markdown migration report to this path")
    ap.add_argument("--strict", action="store_true", help="exit with code 2 if any item needs manual review")
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = ap.parse_args(argv)

    src = sys.stdin.read() if args.jenkinsfile == "-" else Path(args.jenkinsfile).read_text(encoding="utf-8")
    try:
        result = convert(src)
    except (ParseError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    yaml_text = result.to_yaml()
    if args.output:
        Path(args.output).write_text(yaml_text, encoding="utf-8")
    else:
        sys.stdout.write(yaml_text)
    if args.report:
        Path(args.report).write_text(build_report(args.jenkinsfile, result), encoding="utf-8")

    manual = result.manual_items
    print(f"converted: {len(result.findings) - len(manual)} automatic, {len(manual)} need manual review",
          file=sys.stderr)
    return 2 if (args.strict and manual) else 0
