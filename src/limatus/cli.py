"""Limatus CLI entry point.

    limatus scan --draft <file> --profile <style-profile.yml> [--require-judge] [...]
    limatus compare --profile <style-profile.yml> --baseline <file> --candidate <file> [...]
    limatus diagnose  (alias for scan)
    limatus options  --draft <file> --profile <style-profile.yml> \\
                      --diagnosis <diagnosis.json> --decisions <decisions.json> \\
                      --skill <editorial-rewrite-skill.yml> [...]

See editorial_commands.py for each subcommand's full flag set.
"""
from __future__ import annotations

import sys

from . import __version__
from .editorial_judge import JudgeUnavailableError
from .editorial_style import StyleProfileValidationError
from .editorial_commands import (
    editorial_apply,
    editorial_diagnose,
    editorial_diff,
    editorial_options,
    editorial_compare,
    editorial_scan,
    editorial_standfirst,
    editorial_verify,
)
from .editorial_canary import main as editorial_canary
from .editorial_eval import main as editorial_eval

COMMANDS = {
    "scan": editorial_scan,
    "diagnose": editorial_diagnose,
    "options": editorial_options,
    "apply": editorial_apply,
    "diff": editorial_diff,
    "compare": editorial_compare,
    "verify": editorial_verify,
    "standfirst": editorial_standfirst,
    "eval": editorial_eval,
    "canary": editorial_canary,
}


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"-h", "--help"}:
        print(__doc__)
        return 0
    if args[0] in {"-V", "--version"}:
        print(f"limatus {__version__}")
        return 0

    command, flags = args[0], args[1:]
    handler = COMMANDS.get(command)
    if handler is None:
        print(f"limatus: unknown command '{command}'. Try one of: {', '.join(sorted(COMMANDS))}")
        return 1

    try:
        result = handler(flags)
    except (StyleProfileValidationError, JudgeUnavailableError, ValueError) as exc:
        print(f"limatus: {exc}", file=sys.stderr)
        return 1
    return result if isinstance(result, int) else 0


if __name__ == "__main__":
    sys.exit(main())
