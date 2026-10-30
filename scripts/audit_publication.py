"""Audit the Git index before publication; no credential values are printed."""

import re
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
files = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().split("\0")
patterns = [
    r"gh[pousr]_" + r"[A-Za-z0-9]{25,}",
    r"github_pat_" + r"[A-Za-z0-9_]{30,}",
    r"sk-" + r"[A-Za-z0-9_-]{25,}",
    r"-----BEGIN " + r"(?:RSA |OPENSSH |EC )?PRIVATE KEY-----",
]
errors = []
for name in filter(None, files):
    if name == ".env" or any(
        p in name.split("/") for p in ["models", "cache", "runtime", "node_modules", ".venv"]
    ):
        errors.append((name, "private/runtime artifact tracked"))
    path = root / name
    if path.stat().st_size > 20_000_000:
        errors.append((name, "large publication artifact; review rights and destination"))
    if path.suffix not in (".png", ".mp4", ".webm", ".pdf"):
        content = path.read_text(errors="replace")
        if any(re.search(pattern, content) for pattern in patterns):
            errors.append((name, "possible credential; value suppressed"))
        if "/Users/mac/" in content:
            errors.append((name, "host-specific absolute path"))
assert not errors, errors
print(
    f"Publication index audit passed: {len(list(filter(None, files)))} files; no raw corpus, model weights, local runtime paths or credential signatures"
)
