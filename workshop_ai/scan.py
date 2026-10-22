"""Redaction checks (spec section 8). Matched values are never returned or printed."""

import fnmatch
import re
import shutil
import subprocess
from pathlib import Path, PurePosixPath

MAX_PACKAGE_BYTES = 256 * 1024

FORBIDDEN_NAMES = (
    ".env", ".env.*", "auth.json", ".credentials.json", "credentials*.json", "settings.local.json",
    "*.pem", "*.key", "*.p12", "*.pfx", "*.kdbx", "id_rsa*", "id_dsa*", "id_ecdsa*", "id_ed25519*",
    ".netrc", "_netrc", ".npmrc", ".pypirc", ".git-credentials", "my-notes.txt",
)
ALLOWED_NAMES = (".env.example",)
FORBIDDEN_DIRS = (".git", ".ssh", ".workshop-ai")

# (rule name, pattern); a match blocks.
SECRET_RULES = (
    ("private-key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("anthropic-key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}")),
    ("openai-key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}")),
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}")),
    ("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}")),
    ("generic-secret", re.compile(
        r"(?i)\b(?:api[_-]?key|secret|token|password)\b\s*[:=]\s*['\"]?[^\s'\"]{12,}")),
)
# (rule name, pattern); a match warns.
PATH_RULES = (
    ("windows-user-path", re.compile(r"(?i)\b[a-z]:[\\/]users[\\/][^\\/\s<%]+")),
    ("mac-user-path", re.compile(r"/Users/[^/\s<]+")),
    ("linux-user-path", re.compile(r"/home/[^/\s<]+")),
)


def forbidden_reason(rel_path):
    """Why a project-relative path may not be selected as context, or None."""
    parts = PurePosixPath(str(rel_path).replace("\\", "/")).parts
    for part in parts[:-1]:
        if part.lower() in FORBIDDEN_DIRS:
            return f"files under {part}/ are never shared"
    name = parts[-1] if parts else ""
    if name.lower() in ALLOWED_NAMES:
        return None
    for pattern in FORBIDDEN_NAMES:
        if fnmatch.fnmatch(name.lower(), pattern):
            return f"{name} matches a credential file name ({pattern})"
    return None


def scan_text(text, label):
    """Return (blocks, warnings): lists of 'label:line: rule' strings."""
    blocks, warnings = [], []
    for number, line in enumerate(text.splitlines(), start=1):
        for rule, pattern in SECRET_RULES:
            if pattern.search(line):
                blocks.append(f"{label}:{number}: {rule}")
                break
        for rule, pattern in PATH_RULES:
            if pattern.search(line):
                warnings.append(f"{label}:{number}: {rule}")
                break
    return blocks, warnings


def scan_file(path, label):
    try:
        text = Path(path).read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return [f"{label}: binary or non-UTF-8 file (not allowed in a package)"], []
    return scan_text(text, label)


def run_gitleaks(folder, config):
    """'pass', 'fail', 'not installed' or 'error'. Findings are not printed by this tool."""
    exe = shutil.which("gitleaks")
    if not exe:
        return "not installed"
    cmd = [exe, "dir", str(folder), "--no-banner", "--redact", "--exit-code", "1"]
    if config and Path(config).is_file():
        cmd += ["--config", str(config)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return "error"
    return {0: "pass", 1: "fail"}.get(result.returncode, "error")
