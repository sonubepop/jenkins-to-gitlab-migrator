"""Minimal, dependency-free YAML writer for GitLab CI files.

Only handles what .gitlab-ci.yml needs: dicts, lists, strings, ints, bools.
Kept dependency-free so the converter also runs in the browser (Pyodide).
"""

from __future__ import annotations

import re

_INDICATORS = set("-?:,[]{}#&*!|>'\"%@`")
_RESERVED = {"true", "false", "yes", "no", "on", "off", "null", "~", "y", "n"}
_NUMBER = re.compile(r"^[-+]?(\d[\d_]*)?(\.\d*)?([eE][-+]?\d+)?$|^0x[0-9a-fA-F]+$|^0o[0-7]+$")


def _is_plain(s: str) -> bool:
    return bool(
        s
        and s[0] not in _INDICATORS
        and s == s.strip()
        and ": " not in s
        and " #" not in s
        and not s.endswith(":")
        and "\t" not in s
        and s.lower() not in _RESERVED
        and not _NUMBER.match(s)
    )


def _scalar(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    s = str(value)
    if _is_plain(s):
        return s
    if "'" not in s:
        return "'" + s + "'"
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _emit(value, indent: int, out: list[str]) -> None:
    pad = "  " * indent
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(key, str) and key.startswith("#"):
                out.append(pad + key)  # comment line, value ignored
                continue
            k = _scalar(key)
            if isinstance(item, (dict, list)) and item:
                out.append(f"{pad}{k}:")
                _emit(item, indent + 1, out)
            elif isinstance(item, str) and "\n" in item:
                out.append(f"{pad}{k}: |")
                for ln in item.rstrip("\n").split("\n"):
                    out.append(f"{pad}  {ln}" if ln else "")
            else:
                out.append(f"{pad}{k}: {_empty(item) if isinstance(item, (dict, list)) else _scalar(item)}")
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, dict) and item:
                sub: list[str] = []
                _emit(item, indent + 1, sub)
                first = sub[0].lstrip()
                out.append(f"{pad}- {first}")
                out.extend(sub[1:])
            elif isinstance(item, str) and "\n" in item:
                out.append(f"{pad}- |")
                for ln in item.rstrip("\n").split("\n"):
                    out.append(f"{pad}    {ln}" if ln else "")
            else:
                out.append(f"{pad}- {_scalar(item)}")
    else:
        out.append(pad + _scalar(value))


def _empty(v) -> str:
    return "{}" if isinstance(v, dict) else "[]"


def dump(data: dict, header: str = "") -> str:
    out: list[str] = []
    if header:
        out.extend("# " + ln if ln else "#" for ln in header.rstrip("\n").split("\n"))
        out.append("")
    first = True
    for key, value in data.items():
        if not first and isinstance(value, dict):
            out.append("")  # blank line between jobs for readability
        _emit({key: value}, 0, out)
        first = False
    return "\n".join(out) + "\n"
