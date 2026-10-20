"""Fail if any tracked text file contains an em dash (U+2014)."""

import subprocess
import sys

EM_DASH = chr(0x2014)


def scan(files: list[str]) -> int:
    bad = 0
    for name in files:
        try:
            text = open(name, encoding="utf-8").read()
        except (UnicodeDecodeError, FileNotFoundError, IsADirectoryError):
            continue
        for number, line in enumerate(text.splitlines(), 1):
            if EM_DASH in line:
                print(f"{name}:{number}: em dash")
                bad += 1
    print(f"{bad} em dash(es) found")
    return 1 if bad else 0


def main() -> int:
    files = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    return scan(files)


if __name__ == "__main__":
    sys.exit(main())
