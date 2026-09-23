#!/usr/bin/env python3
"""
Generates this fork's visual assets from seeded noise.

Nothing here is sourced from anywhere — the marble slab and the dial are both
rendered from scratch by this script, so the tree carries no third-party
material and the look is reproducible from source.

    python3 tools/make-assets.py            # render both into assets/
    python3 tools/make-assets.py --dial     # just the dial
    python3 tools/make-assets.py --marble   # just the marble
    python3 tools/make-assets.py --check    # report sizes, write nothing

Embedding into the JUCE BinaryData blobs is a separate step:

    python3 tools/embed-assets.py
"""
import argparse
import math
import pathlib
import sys

import numpy as np
from PIL import Image, ImageFilter

ROOT = pathlib.Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

# ----------------------------------------------------------------- noise ---

def _lattice(rng, shape, freq):
    """One octave of value noise: a small random lattice, bicubically upsampled."""
    h, w = shape
    gh, gw = max(2, int(h * freq)), max(2, int(w * freq))
    grid = rng.random((gh, gw)).astype(np.float32)
    img = Image.fromarray((grid * 255).astype(np.uint8), mode="L")
    img = img.resize((w, h), Image.BICUBIC)
    return np.asarray(img, dtype=np.float32) / 255.0


def fbm(rng, shape, base_freq=0.008, octaves=6, gain=0.5, lacunarity=2.0):
    """Fractal Brownian motion, normalised to 0..1."""
    total = np.zeros(shape, dtype=np.float32)
    amplitude, freq, norm = 1.0, base_freq, 0.0
    for _ in range(octaves):
        total += amplitude * _lattice(rng, shape, freq)
        norm += amplitude
        amplitude *= gain
        freq *= lacunarity
    total /= norm
    total -= total.min()
    peak = total.max()
    return total / peak if peak > 0 else total


def blur(a, radius):
    img = Image.fromarray(np.clip(a * 255.0, 0, 255).astype(np.uint8), mode="L")
    return np.asarray(img.filter(ImageFilter.GaussianBlur(radius)), dtype=np.float32) / 255.0


# ------------------------------------------------------------------ dial ---
#
# Geometry as a fraction of the image half-width. The image is deliberately
# wider than the metal so the contact shadow lives inside the alpha channel:
#
#     < 0.600   matte black anodised cap
#   0.600-0.660 chamfer into the collar
#   0.660-0.740 polished chrome collar
#     > 0.740   transparent, carrying the contact shadow
#
# So cap+collar diameter is 0.74 of the image, and the C++ side draws the
# image at body_diameter / 0.74 to land the metal on the skin's knob size.

CAP_R = 0.600
CHAMFER_R = 0.672
COLLAR_R = 0.740

# Single light source, upper left, tilted slightly toward the viewer.
# Everything derives from this one vector: inconsistent lighting is the
# fastest way to make a render look synthetic.
LIGHT = np.array([-0.55, -0.75, 0.36], dtype=np.float32)
LIGHT /= np.linalg.norm(LIGHT)
VIEW = np.array([0.0, 0.0, 1.0], dtype=np.float32)
HALF = (LIGHT + VIEW) / np.linalg.norm(LIGHT + VIEW)


def _chrome_environment(ry):
    """
    A polished ring is a mirror, so it is shaded by reflecting the view into a
    procedural studio rather than by a Phong term. This is a vertical strip:
    bright sky, a hard softbox band at the horizon, dark floor.

    Sampling it by the reflected Y is what produces chrome's signature
    light / dark-equator / light banding — the thing that separates polished
    metal from a grey gradient.
    """
    sky = 0.95 - 0.25 * np.clip(ry, 0.0, 1.0)
    floor = 0.10 + 0.16 * np.clip(-ry, 0.0, 1.0)
    horizon = np.exp(-((ry / 0.085) ** 2)) * 1.00
    lum = np.where(ry >= 0.0, sky, floor) + horizon

    # cool in the sky reflection, warm off the floor: perfectly neutral chrome
    # reads as plastic
    tint = np.stack([
        np.where(ry >= 0.0, 0.97, 1.00),
        np.where(ry >= 0.0, 0.985, 0.97),
        np.where(ry >= 0.0, 1.00, 0.93),
    ], axis=-1)
    return np.clip(lum[..., None] * tint, 0.0, 4.0)


def render_dial(size=512, supersample=4, seed=0xD1A1):
    rng = np.random.default_rng(seed)
    n = size * supersample

    ax = (np.arange(n, dtype=np.float32) + 0.5) / n * 2.0 - 1.0
    x, y = np.meshgrid(ax, ax)
    r = np.sqrt(x * x + y * y)
    with np.errstate(invalid="ignore", divide="ignore"):
        ux, uy = np.where(r > 0, x / r, 0.0), np.where(r > 0, y / r, 0.0)

    rgb = np.zeros((n, n, 3), dtype=np.float32)
    alpha = np.zeros((n, n), dtype=np.float32)

    grain = fbm(rng, (n, n), base_freq=0.02, octaves=5)

    # --- matte anodised cap -------------------------------------------------
    cap = r < CHAMFER_R
    dome = 0.45                                   # gently domed face
    nz = np.ones_like(x)
    nx, ny = x * dome, y * dome
    inv = 1.0 / np.sqrt(nx * nx + ny * ny + nz * nz)
    nx, ny, nz = nx * inv, ny * inv, nz * inv

    lambert = np.clip(nx * LIGHT[0] + ny * LIGHT[1] + nz * LIGHT[2], 0.0, 1.0)
    spec = np.clip(nx * HALF[0] + ny * HALF[1] + nz * HALF[2], 0.0, 1.0) ** 6

    # Near-black, never pure black: #000 reads as a hole punched in the panel.
    # This is LINEAR light — it is gamma-encoded at the end — so anodised black
    # sits around 0.008 here, not the ~0.05 the sRGB value would suggest.
    albedo = 0.0052 * (1.0 + 0.10 * (grain * 2.0 - 1.0))
    angle = np.arctan2(uy, ux)
    albedo *= 1.0 + 0.008 * np.sin(angle * 240.0 + grain * 6.0)   # fine brushing

    face = albedo + 0.024 * lambert ** 1.5 + 0.038 * spec

    # contact shading where the face turns into the chamfer
    edge = np.clip((r - CAP_R * 0.92) / (CHAMFER_R - CAP_R * 0.92), 0.0, 1.0)
    face *= 1.0 - 0.55 * edge ** 2

    rgb[cap] = np.stack([face, face, face], axis=-1)[cap]
    alpha[cap] = 1.0

    # --- polished chrome collar --------------------------------------------
    collar = (r >= CHAMFER_R) & (r < COLLAR_R)
    # treat the collar cross-section as a torus: map radius to a surface angle
    t = np.clip((r - CHAMFER_R) / (COLLAR_R - CHAMFER_R), 0.0, 1.0)
    phi = (t - 0.5) * math.pi                     # -90deg inner .. +90deg outer
    cphi, sphi = np.cos(phi), np.sin(phi)
    cnx, cny, cnz = cphi * ux, cphi * uy, sphi

    # reflect the view vector about the surface normal, then sample the studio
    dot = cnx * VIEW[0] + cny * VIEW[1] + cnz * VIEW[2]
    ry = VIEW[1] - 2.0 * dot * cny
    env = _chrome_environment(ry)

    hot = np.clip(cnx * HALF[0] + cny * HALF[1] + cnz * HALF[2], 0.0, 1.0) ** 220
    metal = env * (1.0 + 0.02 * (grain[..., None] * 2.0 - 1.0)) + hot[..., None] * 1.6

    # a few fine circumferential turning marks — invisible at 28px, and exactly
    # what sells the material on a retina display
    marks = np.sin(r * 620.0 + grain * 3.0) * 0.5 + 0.5
    metal *= (1.0 + 0.018 * (marks[..., None] - 0.5))

    # fresnel-ish darkening at the very outer edge so the ring separates
    # cleanly from whatever is behind it
    metal *= (1.0 - 0.55 * np.clip((t - 0.93) / 0.07, 0.0, 1.0) ** 2)[..., None]

    rgb[collar] = metal[collar]
    alpha[collar] = 1.0

    # --- chamfer: a fine dark line where cap meets collar -------------------
    cham = (r >= CAP_R) & (r < CHAMFER_R)
    ct = np.clip((r - CAP_R) / (CHAMFER_R - CAP_R), 0.0, 1.0)
    dark = 0.02 + 0.10 * ct ** 3
    rgb[cham] = np.stack([dark, dark, dark], axis=-1)[cham]
    alpha[cham] = 1.0

    # --- contact shadow, offset down and right ------------------------------
    off = 0.012
    sr = np.sqrt((x - off) ** 2 + (y - off * 1.6) ** 2)
    shadow = 0.34 * np.exp(-(((sr - COLLAR_R) / 0.050) ** 2))
    shadow[sr < COLLAR_R] = 0.34
    outside = r >= COLLAR_R
    alpha[outside] = np.clip(shadow[outside], 0.0, 1.0)
    rgb[outside] = 0.0

    # --- resolve -------------------------------------------------------------
    srgb = np.clip(rgb, 0.0, 1.0) ** (1.0 / 2.2)
    out = np.dstack([srgb, np.clip(alpha, 0.0, 1.0)])
    img = Image.fromarray((out * 255.0 + 0.5).astype(np.uint8), mode="RGBA")
    return img.resize((size, size), Image.LANCZOS)


# ---------------------------------------------------------------- marble ---

def render_marble(width=2048, height=1200, seed=0xCA22A2A):
    rng = np.random.default_rng(seed)
    shape = (height, width)

    ay = (np.arange(height, dtype=np.float32) / height)
    ax = (np.arange(width, dtype=np.float32) / width)
    gx, gy = np.meshgrid(ax, ay)

    # Domain warp first. Without it every vein is a parallel stripe, which is
    # the clearest tell of procedural marble.
    warp = 0.09
    wx = gx + warp * (fbm(rng, shape, 0.004, 5) - 0.5)
    wy = gy + warp * (fbm(rng, shape, 0.004, 5) - 0.5)

    theta = math.radians(26.0)
    axis = wx * math.cos(theta) + wy * math.sin(theta)

    def veins(scale, power, turb_octaves, turbulence):
        """
        Classic sine-turbulence marble. The directional term must DOMINATE the
        turbulence: let turbulence win and the bands close into contour loops
        that read as clouds, not veins. Carrara's veins run, wander and branch.
        """
        v = axis * scale + turbulence * (fbm(rng, shape, 0.005, turb_octaves) - 0.5)
        return np.abs(np.sin(math.pi * v)) ** power

    primary = blur(veins(6.0, 10, 6, 1.5), 3.5)
    hairline = veins(17.0, 26, 5, 1.1)
    dust = veins(41.0, 48, 4, 0.8)

    # Vein families with clean white fields between them. Uniform density is
    # the other big procedural tell — real Carrara is mostly white.
    cluster_a = fbm(rng, shape, 0.0018, 3) ** 2.4
    cluster_b = fbm(rng, shape, 0.0030, 3) ** 2.2
    primary *= (0.10 + 0.90 * cluster_a) ** 1.5
    hairline *= (cluster_b ** 2.2) * 0.30
    dust *= 0.10

    # every real vein carries a diffuse mineral halo
    halo = np.clip(blur(primary, 9.0) - primary, 0.0, 1.0) * 0.25

    base_mix = fbm(rng, shape, 0.003, 2)
    light = np.array([0.973, 0.965, 0.953], dtype=np.float32)
    dark = np.array([0.929, 0.921, 0.906], dtype=np.float32)
    field = light[None, None, :] * base_mix[..., None] + dark[None, None, :] * (1.0 - base_mix[..., None])

    # Uneven lighting: brightest slightly up-left, ~4.5% falloff to the far
    # corners. A perfectly evenly lit slab does not exist.
    fall = 1.0 - 0.045 * (((gx - 0.42) ** 2) * 1.1 + ((gy - 0.38) ** 2) * 1.4) / 0.35
    field *= np.clip(fall, 0.0, 1.2)[..., None]

    # grey with a faint green cast, never blue-grey: blue-grey veining is the
    # look that reads as fake marble
    vein_colour = np.array([0.47, 0.49, 0.48], dtype=np.float32)
    amount = np.clip(primary * 0.52 + hairline * 0.26 + dust * 0.12, 0.0, 1.0)
    out = field * (1.0 - amount[..., None]) + vein_colour[None, None, :] * amount[..., None]
    out += halo[..., None] * np.array([0.02, 0.015, 0.008], dtype=np.float32)

    # polish sheen along the slab axis
    streak = blur(rng.random(shape).astype(np.float32), 24.0)
    out *= (1.0 + 0.006 * (streak - 0.5))[..., None]

    # grain, which doubles as dither and kills JPEG banding on the smooth field
    out += rng.normal(0.0, 1.3 / 255.0, size=out.shape).astype(np.float32)

    return Image.fromarray((np.clip(out, 0, 1) * 255.0 + 0.5).astype(np.uint8), mode="RGB")


# ------------------------------------------------------------------ main ---

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dial", action="store_true")
    parser.add_argument("--marble", action="store_true")
    parser.add_argument("--check", action="store_true", help="report sizes, write nothing")
    args = parser.parse_args()

    both = not (args.dial or args.marble)
    ASSETS.mkdir(exist_ok=True)

    if args.dial or both:
        dial = render_dial()
        path = ASSETS / "dial.png"
        if not args.check:
            dial.save(path, optimize=True)
        size = path.stat().st_size if path.exists() else 0
        print(f"dial   {dial.size[0]}x{dial.size[1]} RGBA  {size / 1024:.0f} KB  -> {path.relative_to(ROOT)}")
        if size > 140 * 1024:
            print("  WARNING: dial is larger than budget (140 KB)", file=sys.stderr)

    if args.marble or both:
        marble = render_marble()
        path = ASSETS / "marble.jpg"
        if not args.check:
            marble.save(path, quality=82, optimize=True, subsampling=2, progressive=False)
        size = path.stat().st_size if path.exists() else 0
        print(f"marble {marble.size[0]}x{marble.size[1]} RGB   {size / 1024:.0f} KB  -> {path.relative_to(ROOT)}")
        if size > 380 * 1024:
            print("  WARNING: marble is larger than budget (380 KB)", file=sys.stderr)


if __name__ == "__main__":
    main()
