#!/usr/bin/env python3
import sys
import tomllib  # For parsing TOML files (Python 3.11+)


def extract_ucc_revision(file_path):
    try:
        with open(file_path, "rb") as f:
            data = tomllib.load(f)

        # Navigate to the tool.uv.sources section
        uv_sources = data.get("tool", {}).get("uv", {}).get("sources", {})
        if "ucc" not in uv_sources:
            print("Error: 'ucc' entry not found in 'tool.uv.sources'.", file=sys.stderr)
            sys.exit(1)

        # Extract the revision hash
        ucc_entry = uv_sources["ucc"]
        revision = ucc_entry.get("rev")
        if not revision:
            print("Error: 'rev' key is missing in 'ucc' entry.", file=sys.stderr)
            sys.exit(1)

        print(revision)
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.", file=sys.stderr)
        sys.exit(1)
    except tomllib.TOMLDecodeError:
        print(f"Error: Failed to parse TOML file '{file_path}'.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(
            "Usage: python extract_ucc_revision.py <path_to_pyproject.toml>",
            file=sys.stderr,
        )
        sys.exit(1)

    file_path = sys.argv[1]
    extract_ucc_revision(file_path)
