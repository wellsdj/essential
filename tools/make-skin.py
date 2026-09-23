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
    "aa88ff": "2f86e0",
    "bda3ff": "5aa6ea",
    "906de9": "1f6cbd",
    "ba9fff": "5aa6ea",
    "9f88ff": "2f86e0",
    # modulation + envelopes: teal family, cooled and brightened
    "64ffda": "15b39c",
    "1de9b6": "12a582",
    "1de952": "1f9e58",
    "1dc2e9": "1f8fb5",
    "00e686": "0f9c5e",
    # effects
    "ff99e9": "c94fa8",   # delay
    "ff5252": "d4414f",   # distortion
    "ffb74d": "c8821a",   # filter
    "fff6e1": "9c8f76",   # equaliser
    "ffd740": "c9a017",   # flanger
    "40cfff": "2b93c4",   # phaser
    "8fa0ff": "6274cf",   # reverb
    "ff8180": "c96470",
    "ea1616": "cc2b3b",   # modulation drag
    # neutral greys, cooled to sit on the bluer chassis
    "848789": "6d7681",
    "848686": "7c848e",
    "939699": "525b66",
    "aaacad": "434c57",
    "4c4f52": "d5d1cb",
    "262a2e": "e6e2dc",
    "2c3033": "f1eeea",
    "3e4245": "e9e5e0",
    "1d2125": "11161c",
    "606265": "9aa3ae",
    "d3d6d6": "2b3138",
    "dfdfdf": "14181d",
}

# Applied after the palette so a section can opt out of a global remap.
SECTIONS = {
    # These two sit on the wood fascia, so they contribute no body of their
    # own and their type goes light — dark ink on walnut is unreadable.
    "Keyboard": {
        "Body": "00000000",
        "Body Heading Background": "00000000",
        "Body Text": "fff3ece1",
        "Heading Text": "fffbf7f0",
        "Label Background": "4d1e1610",
        "Text Component Background": "662a1f16",
        "Text Component Text": "fff6f0e7",
        "Linear Slider Unselected": "80241a12",
        "Rotary Arc Unselected": "99785c42",
        "Widget Background": "cc17110c",
        # the key faces themselves, which this override also governs
        "Widget Secondary 1": "fff2efe9",   # naturals
        "Widget Secondary 2": "ff17110c",   # sharps
        "Widget Accent 1": "ff6b5946",      # separators
        "Widget Accent 2": "28ffffff",
        "Widget Primary 1": "ff2f86e0",     # pressed
    },
    "Macro": {
        "Body": "00000000",
        "Body Heading Background": "00000000",
        "Body Text": "fff3ece1",
        "Heading Text": "fffbf7f0",
        "Label Background": "4d1e1610",
        "Text Component Background": "662a1f16",
        "Text Component Text": "fff6f0e7",
        "Linear Slider Unselected": "80241a12",
        "Rotary Arc Unselected": "99785c42",
    },
}

# Grounds and geometry: a deeper, bluer chassis with softer corners.
GLOBAL = {
    # --- chassis -----------------------------------------------------------
    # The marble image is the real surface; this is only the fallback if it
    # fails to decode, so it is a marble mid-tone rather than a colour anyone
    # should see.
    "Background": "ffece9e4",

    # Panels are pale frosted stone, slightly translucent so the slab reads
    # through them. JUCE composites this on the CPU into the background image,
    # so translucency needs no GL change.
    "Body": "fff7f5f2",
    "Body Heading Background": "ffe9e5e0",
    "Border": "26000000",

    # --- type: dark on stone ------------------------------------------------
    "Body Text": "ff2b3138",
    "Heading Text": "ff14181d",

    # --- displays stay dark -------------------------------------------------
    # Wavetables, envelopes and LFO curves are luminous traces; they need a
    # dark field to read against, exactly as they do on a light hardware panel.
    "Widget Background": "ff11161c",
    "Widget Center Line": "ff8e9aa6",

    # --- interior controls, all opaque -------------------------------------
    "Popup Background": "fff4f2ef",
    "Popup Selector Background": "ffe6e2dc",
    "Text Component Background": "fff1eeea",
    "Text Component Text": "ff23282e",
    "Text Editor Background": "fff1eeea",
    "Modulation Button Unselected": "ffe6e2dc",
    "Modulation Button Selected": "ffd3dae2",
    "Linear Slider Unselected": "ffd5d1cb",
    "Linear Slider": "ff6d7681",
    "Label Background": "ffe9e5e0",
    "Preset Text": "ff1b2026",

    # --- knobs --------------------------------------------------------------
    # Rotary Body is only the fallback colour; the rendered dial covers it.
    "Rotary Body": "ff16191d",
    "Rotary Body Border": "ff08090b",
    "Rotary Arc Unselected": "ffc6c9cd",
    "Rotary Arc Unselected Disabled": "ffdcdedf",
    "Rotary Hand": "fff4f8fc",

    # --- chrome, buttons, shadows ------------------------------------------
    "Icon Button Off": "ff6d7681",
    "Icon Button Off Hover": "ff434c57",
    "Icon Selector Icon": "ff6d7681",
    "Power Button Off": "ff9aa3ae",
    "UI Button": "ff6d7681",
    "UI Button Hover": "ff525b66",
    "UI Button Press": "ff3a424c",
    "UI Button Text": "fff7f9fb",
    # Shadows on a light ground want to be soft and short, not the deep pools
    # a dark chassis could carry.
    "Shadow": "38161b21",
    "Lighten Screen": "14ffffff",
    "Overlay Screen": "59000000",

    # --- geometry -----------------------------------------------------------
    "Knob Body Size": 29.0,      # the chrome collar needs room, but not at the
                                 # cost of crowding the next knob along
    "Knob Arc Size": 37.0,       # keep the value ring clear of the collar
    "Knob Arc Thickness": 2.0,
    "Knob Handle Length": 0.42,  # a short witness line, not a full spoke
    "Knob Shadow Width": 0.0,    # the dial carries its own contact shadow
    "Body Rounding": 4.0,
    "Widget Rounded Corner": 4.0,
    "Label Rounding": 3.0,
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


def decode_literal(literal: str) -> bytes:
    """Decodes a C string literal back to bytes, to verify what we emitted."""
    out = bytearray()
    for line in literal.strip().rstrip(";").split("\n"):
        line = line.strip().rstrip(";").strip()
        if not (line.startswith('"') and line.endswith('"')):
            raise ValueError(f"unexpected literal line: {line[:40]}")
        inner, i = line[1:-1], 0
        while i < len(inner):
            c = inner[i]
            if c != "\\":
                out.append(ord(c)); i += 1
                continue
            nxt = inner[i + 1]
            if nxt == "n": out.append(10); i += 2
            elif nxt == '"': out.append(34); i += 2
            elif nxt == "\\": out.append(92); i += 2
            elif nxt.isdigit():
                digits = inner[i + 1:i + 4]
                out.append(int(digits, 8)); i += 1 + len(digits)
            else:
                out.append(ord(nxt)); i += 2
    return bytes(out)


def regenerate_binary_data(path: pathlib.Path, skin_bytes: bytes) -> bool:
    """
    Replaces the compiled skin blob and every declared length.

    The lengths are rewritten by matching the symbol, never by assuming what
    the previous value was: deriving it from the file on disk once left a stale
    length behind, JUCE read a truncated JSON, the skin silently failed to
    parse and the whole interface rendered black.
    """
    src = path.read_text()
    start = src.find("static const unsigned char temp_binary_data_3[] =")
    if start < 0:
        return False
    body_start = src.index("\n", start) + 1
    body_end = src.index("\n\n", body_start)
    literal = c_literal(skin_bytes)

    decoded = decode_literal(literal)
    if decoded != skin_bytes:
        raise SystemExit(f"literal round-trip failed: {len(decoded)} vs {len(skin_bytes)} bytes")

    src = src[:body_start] + literal + src[body_end:]
    src, n = re.subn(r"numBytes = \d+; return default_vitalskin;",
                     f"numBytes = {len(skin_bytes)}; return default_vitalskin;", src)
    if n != 1:
        raise SystemExit(f"expected one numBytes site for default_vitalskin, patched {n}")
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
        ok = regenerate_binary_data(p, blob)
        if ok and header.exists():
            h, n = re.subn(r"default_vitalskinSize = \d+",
                           f"default_vitalskinSize = {len(blob)}", header.read_text())
            if n != 1:
                raise SystemExit(f"expected one size declaration in {header}, patched {n}")
            header.write_text(h)
        print(f"{'regenerated' if ok else 'SKIPPED'} {lib} (declares {len(blob)} bytes)")


if __name__ == "__main__":
    main()
