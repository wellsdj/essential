#!/usr/bin/env python3
"""
Generates this fork's default skin.

Vital's look is data-driven: colours and geometry live in a JSON skin, with
per-section overrides that give each part of the synth its own accent. This
script recolours that skin rather than hardcoding anything in C++, then
regenerates the JUCE BinaryData blob so the new look ships as the built-in
default.

    python3 tools/make-skin.py            # write skin + regenerate BinaryData
    python3 tools/make-skin.py --check    # report only, change nothing
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKIN = ROOT / "default.vitalskin"

# Upstream RGB -> this fork's RGB. Alpha is preserved wherever a colour
# carries one, so translucent variants follow automatically.
PALETTE = {
    # brand / primary: violet becomes azure
    "aa88ff": "4fb6ff",
    "bda3ff": "8ad3ff",
    "906de9": "2b8fe0",
    "ba9fff": "8ad3ff",
    "9f88ff": "4fb6ff",
    # modulation + envelopes: teal family, cooled and brightened
    "64ffda": "3fe3d0",
    "1de9b6": "25d9a8",
    "1de952": "2fdc82",
    "1dc2e9": "35bdf0",
    "00e686": "23e08a",
    # effects
    "ff99e9": "ff7ad9",   # delay
    "ff5252": "ff5c6c",   # distortion
    "ffb74d": "ffb03c",   # filter
    "fff6e1": "f2e9d8",   # equaliser
    "ffd740": "ffd93d",   # flanger
    "40cfff": "3fd0ff",   # phaser
    "8fa0ff": "8aa2ff",   # reverb
    "ff8180": "ff7d8f",
    "ea1616": "ff4757",   # modulation drag
    # neutral greys, cooled to sit on the bluer chassis
    "848789": "7d93a8",
    "848686": "6a7f93",
    "939699": "9ab2c8",
    "aaacad": "a8c0d6",
    "4c4f52": "1e2a37",
    "262a2e": "0e151d",
    "2c3033": "141d27",
    "3e4245": "121a24",
    "1d2125": "0b1118",
    "606265": "44566a",
    "d3d6d6": "d6e4f2",
    "dfdfdf": "eaf3fb",
}

# Applied after the palette so a section can opt out of a global remap.
SECTIONS = {
    # the palette darkens 4c4f52/262a2e, which are this section's key faces,
    # so the keyboard states are set explicitly to keep the keys readable
    "Keyboard": {
        "Widget Secondary 1": "ffc2d2e0",   # natural keys
        "Widget Secondary 2": "ff0d141c",   # sharps
        "Widget Accent 1": "ff5a6f84",      # separators
        "Widget Accent 2": "28ffffff",
        "Widget Primary 1": "ff4fb6ff",     # pressed
    },
}

# Grounds and geometry: a deeper, bluer chassis with softer corners.
GLOBAL = {
    # --- chassis: neutral graphite panels, the way a hardware rack reads,
    # rather than Vital's warm grey or a saturated blue
    "Background": "ff141517",
    "Body": "ff232629",
    "Body Heading Background": "ff1a1c1f",
    "Body Text": "ffc8ced6",
    "Heading Text": "ffe9eef4",
    "Widget Background": "ff0f1113",
    "Popup Background": "ff1a1c1f",
    "Popup Selector Background": "ff26292d",
    "Text Component Background": "ff1d2023",
    "Text Editor Background": "ff1d2023",
    "Modulation Button Unselected": "ff1d2023",
    "Modulation Button Selected": "ff2e3339",
    "Linear Slider Unselected": "ff121416",
    "Label Background": "ff1a1c1f",

    # --- knobs
    "Rotary Body": "ff2f343a",          # the bevel gradient is derived from this
    "Rotary Body Border": "ff0a0b0d",
    "Rotary Arc Unselected": "ff41474e",
    "Rotary Arc Unselected Disabled": "ff2a2e33",
    "Rotary Hand": "fff2f7fb",

    "Icon Button Off": "ff8d96a1",
    "Icon Button Off Hover": "ffc4ccd5",
    "Icon Selector Icon": "ff8d96a1",
    "Power Button Off": "ff4d545c",
    "Linear Slider": "ff8d96a1",
    "UI Button": "ff8d96a1",
    "UI Button Hover": "ffabb4bf",
    "UI Button Press": "ff4d545c",
    "Shadow": "b3000000",
    "Lighten Screen": "16ffffff",
    "Overlay Screen": "44000000",

    # --- geometry: the value ring moves outside a smaller body, and the
    # panels square off, which is the bulk of the Serum-like change
    "Knob Body Size": 28.0,
    "Knob Arc Size": 36.0,
    "Knob Arc Thickness": 2.4,
    "Knob Handle Length": 0.68,
    "Knob Mod Amount Arc Size": 43.0,
    "Knob Mod Meter Arc Size": 42.0,
    "Knob Shadow Width": 5.0,
    "Body Rounding": 3.0,
    "Widget Rounded Corner": 3.0,
    "Label Rounding": 2.0,
    "Widget Line Width": 2.0,
    "Widget Fill Fade": 0.4,
}

HEX = re.compile(r"^[0-9a-fA-F]{6,8}$")


def recolour(value):
    """Remaps a colour string through the palette, preserving any alpha."""
    if not isinstance(value, str) or not HEX.match(value):
        return value
    alpha, rgb = value[:-6], value[-6:].lower()
    mapped = PALETTE.get(rgb)
    return alpha + mapped if mapped else value


def walk(node):
    if isinstance(node, dict):
        return {k: walk(v) for k, v in node.items()}
    if isinstance(node, list):
        return [walk(v) for v in node]
    return recolour(node)


def c_literal(data: bytes) -> str:
    """Re-emits the skin as the chunked C string literal JUCE generates."""
    out, line = [], []
    for byte in data:
        ch = chr(byte)
        if ch == '"':
            line.append('\\"')
        elif ch == "\\":
            line.append("\\\\")
        elif ch == "\n":
            line.append("\\n")
        elif 32 <= byte < 127:
            line.append(ch)
        else:
            line.append(f"\\{byte:03o}")
        if len(line) >= 100:
            out.append('"' + "".join(line) + '"')
            line = []
    if line:
        out.append('"' + "".join(line) + '"')
    return "\n".join(out) + ";"


def regenerate_binary_data(path: pathlib.Path, skin_bytes: bytes, old_size: int) -> bool:
    src = path.read_text()
    start = src.find("static const unsigned char temp_binary_data_3[] =")
    if start < 0:
        return False
    body_start = src.index("\n", start) + 1
    body_end = src.index("\n\n", body_start)
    src = src[:body_start] + c_literal(skin_bytes) + src[body_end:]
    src = src.replace(f"numBytes = {old_size}; return default_vitalskin;",
                      f"numBytes = {len(skin_bytes)}; return default_vitalskin;")
    path.write_text(src)
    return True


def main():
    check_only = "--check" in sys.argv
    skin = json.loads(SKIN.read_text())

    old_size = SKIN.stat().st_size
    new = walk(skin)
    new.update(GLOBAL)
    for section, values in SECTIONS.items():
        if isinstance(new.get("overrides", {}).get(section), dict):
            new["overrides"][section].update(values)

    # keep the per-section accents distinct, just retuned by the palette above
    blob = json.dumps(new, separators=(",", ":")).encode()

    changed = sum(
        1 for k, v in new.items()
        if isinstance(v, str) and skin.get(k) != v
    )
    print(f"recoloured {changed} top-level values, {len(new['overrides'])} sections")
    print(f"skin size {old_size} -> {len(blob)} bytes")

    if check_only:
        return

    SKIN.write_bytes(blob)

    for lib in ["standalone/JuceLibraryCode/BinaryData.cpp", "plugin/JuceLibraryCode/BinaryData.cpp"]:
        p = ROOT / lib
        if not p.exists():
            continue
        header = p.with_suffix(".h")
        ok = regenerate_binary_data(p, blob, old_size)
        if ok and header.exists():
            h = header.read_text().replace(
                f"default_vitalskinSize = {old_size}",
                f"default_vitalskinSize = {len(blob)}",
            )
            header.write_text(h)
        print(f"{'regenerated' if ok else 'SKIPPED'} {lib}")


if __name__ == "__main__":
    main()
