"""
Shared helpers for rewriting JUCE's generated BinaryData blobs.

Projucer is not vendored in this fork, so embedded resources are maintained by
script. The rule these helpers exist to enforce: **never patch a declared
length by searching for the value you think is currently there.** Doing that
once left a stale length behind, JUCE read a truncated JSON, the skin silently
failed to parse and the entire interface rendered black. Every size here is
rewritten by matching the symbol, and every emitted blob is decoded back and
compared byte-for-byte before anything is written.

Text resources (the skin) are emitted as chunked C string literals, matching
what JUCE does for JSON. True binary (images, fonts) is emitted as a decimal
byte array, also matching JUCE — a multi-kilobyte string literal would exceed
MSVC's 65535-byte limit if a Windows build is ever attempted.
"""
import pathlib
import re


# --------------------------------------------------------------- literals ---

def c_literal(data: bytes) -> str:
    """Chunked C string literal, as JUCE emits for text resources."""
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
                out.append(ord(c))
                i += 1
                continue
            nxt = inner[i + 1]
            if nxt == "n":
                out.append(10); i += 2
            elif nxt == '"':
                out.append(34); i += 2
            elif nxt == "\\":
                out.append(92); i += 2
            elif nxt.isdigit():
                digits = inner[i + 1:i + 4]
                out.append(int(digits, 8)); i += 1 + len(digits)
            else:
                out.append(ord(nxt)); i += 2
    return bytes(out)


def c_byte_array(data: bytes, per_line: int = 40) -> str:
    """Decimal byte array, as JUCE emits for binary resources."""
    lines = []
    for start in range(0, len(data), per_line):
        chunk = data[start:start + per_line]
        lines.append(",".join(str(b) for b in chunk))
    return "{ " + ",\n".join(lines) + ",0,0 };"


def decode_byte_array(text: str) -> bytes:
    """Decodes the byte-array form back to bytes, ignoring JUCE's two-byte pad."""
    body = text[text.index("{") + 1:text.rindex("}")]
    values = [int(v) for v in body.replace("\n", "").split(",") if v.strip() != ""]
    return bytes(values[:-2])          # trailing 0,0 terminator JUCE appends


# -------------------------------------------------------------- resources ---

def _next_index(src: str) -> int:
    used = [int(m) for m in re.findall(r"temp_binary_data_(\d+)", src)]
    return max(used) + 1 if used else 0


def add_binary_resource(cpp_path: pathlib.Path, header_path: pathlib.Path,
                        symbol: str, data: bytes) -> str:
    """
    Embeds (or replaces) one binary resource, accessible as BinaryData::<symbol>.

    Deliberately does NOT touch namedResourceList, originalFilenames,
    namedResourceListSize or the getNamedResource switch. Those three must stay
    length-consistent with each other or getNamedResourceOriginalFilename walks
    off the end of the array, and nothing in this codebase calls
    getNamedResource — every access is through the extern symbol directly. Less
    surface, no chance of an inconsistent table.
    """
    src = cpp_path.read_text()
    array = c_byte_array(data)

    # Find the declaration FIRST to learn which temp array belongs to this
    # symbol, then rewrite only that array. Matching the array and the
    # declaration in one pattern spans every block in between and deletes them.
    declared = re.search(
        rf"const char\* {re.escape(symbol)} = \(const char\*\) (temp_binary_data_\d+);", src)

    if declared:
        temp_name = declared.group(1)
        block_re = re.compile(
            rf"static const unsigned char {temp_name}\[\] =\n\{{.*?\}};", re.DOTALL)
        if not block_re.search(src):
            raise SystemExit(f"{symbol}: declaration exists but {temp_name} block is missing")
        src = block_re.sub(f"static const unsigned char {temp_name}[] =\n{array}",
                           src, count=1)
        action = "replaced"
    else:
        temp_name = f"temp_binary_data_{_next_index(src)}"
        block = (f"\nstatic const unsigned char {temp_name}[] =\n{array}\n\n"
                 f"const char* {symbol} = (const char*) {temp_name};\n")
        anchor = src.index("const char* getNamedResource")
        # back up to the comment banner JUCE puts above that function
        banner = src.rfind("//====", 0, anchor)
        insert_at = banner if banner != -1 else anchor
        src = src[:insert_at] + block + "\n" + src[insert_at:]
        action = "added"

    # verify the emitted array round-trips before writing anything
    emitted = re.search(
        rf"static const unsigned char {temp_name}\[\] =\n(\{{.*?\}};)", src, re.DOTALL)
    if emitted is None:
        raise SystemExit(f"could not re-find the block just written for {symbol}")
    decoded = decode_byte_array(emitted.group(1))
    if decoded != data:
        raise SystemExit(f"{symbol}: byte array does not round-trip "
                         f"({len(decoded)} vs {len(data)} bytes)")

    cpp_path.write_text(src)

    # --- header: extern + size, both matched on the symbol -------------------
    head = header_path.read_text()
    decl = f"    extern const char*   {symbol};\n    const int            {symbol}Size = {len(data)};\n"
    if f"{symbol}Size" in head:
        head, n = re.subn(rf"    extern const char\*   {re.escape(symbol)};\n"
                          rf"    const int            {re.escape(symbol)}Size = \d+;\n",
                          decl, head)
        if n != 1:
            raise SystemExit(f"expected one declaration of {symbol}, patched {n}")
    else:
        # anchor on the comment above the resource-count block; the
        # declaration spacing in this file is not uniform enough to match on
        marker = "    // Number of elements in the namedResourceList"
        idx = head.index(marker)
        head = head[:idx] + decl + "\n" + head[idx:]
    header_path.write_text(head)

    return action


def verify_resource(cpp_path: pathlib.Path, header_path: pathlib.Path,
                    symbol: str, data: bytes) -> None:
    """Re-reads both files from disk and confirms they agree with the source data."""
    src = cpp_path.read_text()
    match = re.search(
        rf"const char\* {re.escape(symbol)} = \(const char\*\) (temp_binary_data_\d+);", src)
    if not match:
        raise SystemExit(f"{cpp_path}: {symbol} is not declared")
    block = re.search(
        rf"static const unsigned char {match.group(1)}\[\] =\n(\{{.*?\}};)", src, re.DOTALL)
    if decode_byte_array(block.group(1)) != data:
        raise SystemExit(f"{cpp_path}: {symbol} bytes do not match the asset")

    head = header_path.read_text()
    size = re.search(rf"{re.escape(symbol)}Size = (\d+);", head)
    if not size or int(size.group(1)) != len(data):
        raise SystemExit(f"{header_path}: {symbol}Size disagrees with the asset "
                         f"({size.group(1) if size else 'missing'} vs {len(data)})")
