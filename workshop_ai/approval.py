"""Approval prompts (spec section 7).

Every prompt needs a person at a terminal: stdin and stdout must both be terminals. An AI session's
shell tool or a pipe (`echo y | wai ...`) cannot approve. There is deliberately no skip flag.
"""

import sys

from .errors import REFUSED, WaiError


def _is_terminal():
    return sys.stdin.isatty() and sys.stdout.isatty()


def _ask(prompt):
    return input(prompt)


def _require_terminal():
    if not _is_terminal():
        raise WaiError(
            "approval requires an interactive terminal: run this command yourself in a normal terminal, "
            "not from an AI session or a script",
            REFUSED,
        )


def confirm(question):
    """Ask y/N; default No. Returns True only for an explicit yes."""
    _require_terminal()
    answer = _ask(f"{question} [y/N] ").strip().lower()
    return answer in ("y", "yes")


def confirm_typed(question, word):
    """Ask the user to type an exact word (used for the manual secret review)."""
    _require_terminal()
    answer = _ask(f"{question} Type '{word}' to confirm: ").strip().lower()
    return answer == word
