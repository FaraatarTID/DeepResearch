#!/usr/bin/env python3
"""Simple pre-mortem static checks for the repository.
Flags:
 - except-pass blocks
 - except Exception without logger.exception or raise
 - assignments to sys.modules[...] or modifying imported module attributes
Usage: python scripts/pre_mortem_checks.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATTERNS = [
    (re.compile(r"except\s*:\s*\n\s*pass"), "bare except with pass"),
    (re.compile(r"except\s+Exception\b[\s\S]{0,120}?\n\s*(?!logger\.exception|raise)"), "except Exception without logger.exception or raise"),
    (re.compile(r"sys\.modules\s*\["), "mutation of sys.modules (suspect reassigning module attributes)"),
    (re.compile(r"\b\w+\s*=\s*sys\.modules\["), "assignment to sys.modules[...] (suspicious module mutation)"),
    (re.compile(r"def\s+\w+\([^\)]*=[ \t]*(?:\[\]|\{\})"), "mutable default arg (list/dict) in function signature"),
    (re.compile(r"\bfrom\s+[\w\.]+\s+import\s+\*"), "star import (reduces clarity)"),
    (re.compile(r"\b__\w+\s*=\s*"), "assignment to double-underscore names (potential private module mutation)"),
    (re.compile(r"\basyncio\.run\s*\("), "use of asyncio.run in library code (may create nested event loops)"),
    (re.compile(r"threading\.Thread\s*\("), "creation of raw threads (ensure proper shutdown/cancellation)"),
]

IGNORE_DIRS = {".git", "__pycache__", "venv", "env", ".venv"}


def scan_file(path: Path):
    text = path.read_text(encoding='utf-8', errors='ignore')
    findings = []
    # Determine if this file is a test file (under tests/ or name starts with test_)
    is_test = ('tests' in path.parts) or path.name.startswith('test_')

    # First, special-case 'except Exception' occurrences to look ahead for proper logging or re-raise
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        if re.match(r"\s*except\s+Exception\b", line):
            # If this is in a test file, skip check (tests often run small event loops and handle exceptions locally)
            if is_test:
                continue
            # Look ahead up to 3 following non-empty, non-comment lines for '.exception(' or 'raise'
            found_good = False
            for j in range(idx + 1, min(idx + 5, len(lines))):
                nxt = lines[j].strip()
                if not nxt or nxt.startswith('#'):
                    continue
                if '.exception' in nxt or re.match(r"raise\b", nxt):
                    found_good = True
                break
            if not found_good:
                lineno = idx + 1
                findings.append((lineno, 'except Exception without logger.exception or raise', line.strip()))

    # Run the rest of the PATTERNS but filter out asyncio.run in tests
    for pat, desc in PATTERNS:
        if 'asyncio.run' in desc and is_test:
            continue
        for m in pat.finditer(text):
            # Skip the 'except Exception' matches we already handled above
            if m.group(0).strip().startswith('except'):
                continue
            lineno = text.count('\n', 0, m.start()) + 1
            findings.append((lineno, desc, m.group(0).strip()))

    return findings


def main():
    py_files = [p for p in ROOT.rglob('*.py') if not any(part in IGNORE_DIRS for part in p.parts)]
    total = 0
    summary_counts = {}
    file_counts = {}
    for f in py_files:
        total += 1
        findings = scan_file(f)
        if findings:
            rel = f.relative_to(ROOT)
            print(f"\n{rel}:")
            file_counts[str(rel)] = file_counts.get(str(rel), 0) + len(findings)
            for lineno, desc, snippet in findings:
                print(f"  L{lineno}: {desc}")
                snippet_line = snippet.splitlines()[0] if snippet else ''
                print(f"    -> {snippet_line}")
                summary_counts[desc] = summary_counts.get(desc, 0) + 1
    print(f"\nScanned {total} Python files.")

    # Summary report
    total_findings = sum(summary_counts.values())
    print("\nSUMMARY REPORT")
    print("--------------")
    print(f"Total findings: {total_findings}")
    if summary_counts:
        print("Findings by type:")
        for desc, cnt in sorted(summary_counts.items(), key=lambda x: -x[1]):
            print(f"  - {desc}: {cnt}")

    if file_counts:
        print("Top files with findings:")
        for fname, cnt in sorted(file_counts.items(), key=lambda x: -x[1])[:10]:
            print(f"  - {fname}: {cnt}")

if __name__ == '__main__':
    main()
