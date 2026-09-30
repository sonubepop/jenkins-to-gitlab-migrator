"""jenkins2gitlab - convert declarative Jenkinsfiles to .gitlab-ci.yml."""

from .converter import Finding, Result, convert
from .parser import ParseError, parse

__all__ = ["convert", "parse", "Result", "Finding", "ParseError"]
__version__ = "0.1.0"
