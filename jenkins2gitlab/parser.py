"""Small parser for declarative Jenkinsfiles.

It does not try to understand all of Groovy. It reads the nested block
structure that declarative pipelines use:

    name { ... }
    name('arg', key: value) { ... }

and keeps everything else as plain statements (``sh 'make'``, ``FOO = 'bar'``).
That is enough to translate most real-world declarative pipelines.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Union


class ParseError(ValueError):
    pass


@dataclass
class Statement:
    text: str
    line: int


@dataclass
class Block:
    name: str
    args: str = ""
    children: list[Union[Block, Statement]] = field(default_factory=list)
    line: int = 0

    # --- helpers used by the converter -------------------------------
    def blocks(self, name: str | None = None) -> list[Block]:
        return [c for c in self.children if isinstance(c, Block) and (name is None or c.name == name)]

    def block(self, name: str) -> Block | None:
        found = self.blocks(name)
        return found[0] if found else None

    def statements(self) -> list[Statement]:
        return [c for c in self.children if isinstance(c, Statement)]


def strip_comments(src: str) -> str:
    """Remove // and /* */ comments while leaving string literals alone."""
    out = []
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if src.startswith("'''", i) or src.startswith('"""', i):
            q = src[i:i + 3]
            end = src.find(q, i + 3)
            end = n if end == -1 else end + 3
            out.append(src[i:end])
            i = end
        elif c in "'\"":
            j = i + 1
            while j < n and src[j] != c:
                if src[j] == "\\":
                    j += 1
                if src[j] == "\n":
                    break
                j += 1
            out.append(src[i:j + 1])
            i = j + 1
        elif src.startswith("//", i):
            end = src.find("\n", i)
            i = n if end == -1 else end
        elif src.startswith("/*", i):
            end = src.find("*/", i + 2)
            chunk = src[i:n if end == -1 else end + 2]
            out.append("\n" * chunk.count("\n"))  # keep line numbers stable
            i = n if end == -1 else end + 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


class _Reader:
    def __init__(self, src: str):
        self.src = src
        self.i = 0
        self.n = len(src)

    def line(self) -> int:
        return self.src.count("\n", 0, self.i) + 1

    def skip_ws(self) -> None:
        while self.i < self.n and self.src[self.i] in " \t\r\n;":
            self.i += 1

    def skip_string(self, j: int) -> int:
        """Return the index just past the string literal starting at j."""
        s = self.src
        if s.startswith("'''", j) or s.startswith('"""', j):
            end = s.find(s[j:j + 3], j + 3)
            if end == -1:
                raise ParseError(f"unterminated triple-quoted string at line {self.src.count(chr(10), 0, j) + 1}")
            return end + 3
        q = s[j]
        k = j + 1
        while k < self.n and s[k] != q:
            if s[k] == "\\":
                k += 1
            k += 1
        return k + 1

    def read_balanced(self, open_ch: str, close_ch: str) -> str:
        """Read from an opening bracket to its matching close; return the inside."""
        assert self.src[self.i] == open_ch
        depth, j = 0, self.i
        while j < self.n:
            c = self.src[j]
            if c in "'\"":
                j = self.skip_string(j)
                continue
            if c == open_ch:
                depth += 1
            elif c == close_ch:
                depth -= 1
                if depth == 0:
                    inner = self.src[self.i + 1:j]
                    self.i = j + 1
                    return inner
            j += 1
        raise ParseError(f"unbalanced '{open_ch}' starting at line {self.line()}")


def _parse_body(r: _Reader, until_close: bool) -> list[Union[Block, Statement]]:
    items: list[Union[Block, Statement]] = []
    while True:
        r.skip_ws()
        if r.i >= r.n:
            if until_close:
                raise ParseError("missing closing '}'")
            return items
        if r.src[r.i] == "}":
            if not until_close:
                raise ParseError(f"unexpected '}}' at line {r.line()}")
            r.i += 1
            return items

        start, line = r.i, r.line()
        # Read one logical statement: stop at newline / '{' / '}' outside brackets.
        j = r.i
        depth = 0
        while j < r.n:
            c = r.src[j]
            if c in "'\"":
                j = r.skip_string(j)
                continue
            if c in "([":
                depth += 1
            elif c in ")]":
                depth -= 1
            elif depth == 0 and c == "\n" and r.src[start:j].rstrip().endswith((",", "+", "&&", "||")):
                pass  # statement continues on the next line
            elif depth == 0 and c in "{}\n;":
                break
            j += 1
        head = r.src[start:j].strip()
        r.i = j

        if j < r.n and r.src[j] == "{":
            # A block: "name", "name(args)" or "name 'arg'" followed by {...}
            name, args = _split_head(head)
            inner_src = r.read_balanced("{", "}")
            sub = _Reader(inner_src)
            children = _parse_body(sub, until_close=False)
            items.append(Block(name=name, args=args, children=children, line=line))
        else:
            if head:
                items.append(Statement(text=head, line=line))


def _split_head(head: str) -> tuple[str, str]:
    head = head.strip()
    if "(" in head and head.endswith(")"):
        idx = head.index("(")
        return head[:idx].strip(), head[idx + 1:-1].strip()
    parts = head.split(None, 1)
    if not parts:
        return "", ""
    return parts[0], parts[1] if len(parts) > 1 else ""


def parse(src: str) -> Block:
    """Parse a Jenkinsfile and return the ``pipeline`` block."""
    cleaned = strip_comments(src)
    root = Block(name="<root>", children=_parse_body(_Reader(cleaned), until_close=False))
    pipeline = root.block("pipeline")
    if pipeline is None:
        raise ParseError("no 'pipeline { ... }' block found - only declarative pipelines are supported")
    return pipeline
