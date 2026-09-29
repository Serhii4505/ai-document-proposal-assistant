"""Scan the public project tree for secrets, real email addresses and unsafe n8n metadata."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys


TEXT_SUFFIXES = {".csv", ".env", ".example", ".json", ".md", ".py", ".toml", ".txt", ".yaml", ".yml"}
EXCLUDED_DIRECTORIES = {".git", ".pytest_cache", ".venv", "__pycache__", "data", "output"}
RESERVED_EMAIL_DOMAINS = {"example.com", "example.net", "example.org"}

# Build credential markers in pieces so this scanner does not flag its own source.
SECRET_PATTERNS = {
    "private key": re.compile("BEGIN " + "(?:RSA |EC |OPENSSH )?PRIVATE KEY"),
    "Google API key": re.compile("AI" + r"za[0-9A-Za-z_-]{32,}"),
    "GitHub token": re.compile("gh" + r"[pousr]_[0-9A-Za-z]{30,}"),
    "OpenAI-style key": re.compile("sk" + r"-[0-9A-Za-z_-]{20,}"),
    "assigned secret": re.compile(
        r"(?m)^[ \t]*(?:GEMINI_API_KEY|GOOGLE_API_KEY|CLIENT_SECRET|API_KEY|ACCESS_TOKEN)[ \t]*=[ \t]*(?!$|['\"]?[ \t]*$|<|your-|replace-|example)[^ \t\r\n#]{12,}"
    ),
}
EMAIL_PATTERN = re.compile(r"(?i)\b[A-Z0-9._%+-]+@([A-Z0-9.-]+\.[A-Z]{2,})\b")


def iter_public_text_files(root: Path):
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in EXCLUDED_DIRECTORIES for part in path.relative_to(root).parts):
            continue
        if path.name == ".env" or path.suffix.casefold() in TEXT_SUFFIXES or path.name.endswith(".env.example"):
            yield path


def scan_tree(root: Path) -> list[str]:
    root = root.resolve(strict=True)
    findings: list[str] = []
    for path in iter_public_text_files(root):
        relative = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            findings.append(f"{relative}: text file is not valid UTF-8")
            continue
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                findings.append(f"{relative}: possible {label}")
        for match in EMAIL_PATTERN.finditer(text):
            domain = match.group(1).casefold()
            if domain not in RESERVED_EMAIL_DOMAINS:
                findings.append(f"{relative}: non-demo email address")

        if path.name.endswith(".workflow.json"):
            try:
                workflow = json.loads(text)
            except json.JSONDecodeError:
                findings.append(f"{relative}: invalid workflow JSON")
                continue
            if workflow.get("active") is not False:
                findings.append(f"{relative}: public workflow must be inactive")
            if workflow.get("versionId"):
                findings.append(f"{relative}: versionId must be blank")
            if workflow.get("pinData"):
                findings.append(f"{relative}: pinData must be empty")
            for node in workflow.get("nodes", []):
                if node.get("credentials"):
                    findings.append(f"{relative}: node contains credentials")
                if node.get("webhookId"):
                    findings.append(f"{relative}: node contains exported webhookId")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=Path(__file__).parents[1], type=Path)
    args = parser.parse_args()
    findings = scan_tree(args.root)
    if findings:
        print("Public export security scan failed:")
        for finding in findings:
            print(f"- {finding}")
        return 1
    print("Public export security scan passed: no secrets, real emails or unsafe n8n metadata found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
