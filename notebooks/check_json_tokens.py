"""
Estimate token counts for a JSON file (rough).
"""

import json
from pathlib import Path


def count_tokens(text: str) -> int:
    # very rough: split by whitespace
    return len(text.split())


def main():
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("json_path", type=Path)
    args = p.parse_args()

    data = args.json_path.read_text(encoding="utf-8")
    tokens = count_tokens(data)
    print(f"File: {args.json_path}")
    print(f"Approx tokens: {tokens}")


if __name__ == "__main__":
    main()

