#!/usr/bin/env python3
"""
Embeds the generated assets into every JUCE BinaryData copy.

    python3 tools/embed-assets.py            # embed and verify
    python3 tools/embed-assets.py --verify   # verify only, write nothing

Run tools/make-assets.py first. Three copies of BinaryData exist (standalone,
plugin, tests) and all are kept in step, because a divergent copy is invisible
until the day someone builds that target.
"""
import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from binary_data import add_binary_resource, verify_resource   # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
TARGETS = ["standalone", "plugin", "tests"]
RESOURCES = [
    ("dial_png", ROOT / "assets" / "dial.png"),
    ("marble_jpg", ROOT / "assets" / "marble.jpg"),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()

    payloads = []
    for symbol, path in RESOURCES:
        if not path.exists():
            raise SystemExit(f"missing {path.relative_to(ROOT)} — run tools/make-assets.py first")
        payloads.append((symbol, path, path.read_bytes()))

    for target in TARGETS:
        cpp = ROOT / target / "JuceLibraryCode" / "BinaryData.cpp"
        header = ROOT / target / "JuceLibraryCode" / "BinaryData.h"
        if not cpp.exists():
            print(f"  skipped {target}: no BinaryData.cpp")
            continue

        for symbol, path, data in payloads:
            if args.verify:
                verify_resource(cpp, header, symbol, data)
                print(f"  ok       {target}/{symbol}  {len(data) / 1024:.0f} KB")
            else:
                action = add_binary_resource(cpp, header, symbol, data)
                verify_resource(cpp, header, symbol, data)
                print(f"  {action:<8} {target}/{symbol}  {len(data) / 1024:.0f} KB")

    total = sum(len(d) for _, _, d in payloads)
    print(f"\n{len(payloads)} resources, {total / 1024:.0f} KB embedded per target")


if __name__ == "__main__":
    main()
