# Changes in this fork

Required by GPLv3 section 5(a): "carry prominent notices stating that you
modified it, and giving a relevant date."

Forked from https://github.com/mtytel/vital at commit `636ca0e`.

All changes below were made on **2026-09-22** by Wells Thompson.

## Product identity

Upstream builds the open-source target as "Vial" — Matt Tytel's own
concession to the trademark on "Vital". This fork renames it again so the
distributed binary is clearly not his product.

| File | Change |
| --- | --- |
| `standalone/builds/osx/Info-App.plist` | `CFBundleName`, `CFBundleDisplayName` → `Essential`; `CFBundleIdentifier` → `com.wellsdj.essential` |
| `standalone/builds/osx/Essential.xcodeproj/project.pbxproj` | `PRODUCT_NAME`, target name, product reference → `Essential`; bundle identifier updated |
| `standalone/builds/osx/Vial.xcodeproj` | directory renamed to `Essential.xcodeproj` |
| `standalone/vital.jucer`, `plugin/vital.jucer` | project name, bundle identifiers, `companyName` updated |
| `standalone/vital.desktop` | Linux launcher name |
| `src/common/load_save.cpp` | application name and the `Music/` and `Documents/` data directories → `Essential` |
| `src/interface/editor_sections/download_section.cpp` | content directory name → `Essential` |

## Service connections removed

Upstream's terms forbid builds from connecting to `vital.audio`,
`account.vital.audio` or `store.vital.audio`.

| File | Change |
| --- | --- |
| `standalone/builds/osx/Essential.xcodeproj/project.pbxproj` | build define `REQUIRE_AUTH=1` replaced with `NO_AUTH=1`, which is upstream's own switch for compiling out the Firebase account code (`src/interface/editor_sections/authentication_section.h`). `REQUIRE_AUTH` is defined by the build but never read anywhere in the source. |
| `src/interface/editor_sections/wavetable_edit_section.cpp`, `src/standalone/main.cpp` | the `clm ` chunk written into exported wavetables said `vital.audio`; now says `Essential`, so exported files do not carry his domain |

Verified against the built binary: no `vital.audio`, `account.vital` or
`store.vital` strings remain.

## Interface restyle (2026-09-22)

The synthesis engine is still entirely unmodified. These changes are cosmetic.

| File | Change |
| --- | --- |
| `default.vitalskin` | regenerated: graphite chassis in place of the warm grey, azure primary in place of the violet, cooled neutrals, squarer corners, and the value ring moved outside a smaller knob body |
| `tools/make-skin.py` | **new** — generates the skin from a palette map and per-section overrides, then regenerates the JUCE `BinaryData` blob, so the look stays data-driven rather than hardcoded |
| `src/interface/editor_components/synth_slider.cpp` | `drawRotaryShadow` paints a bevelled cylinder with a rim highlight and tick marks around the value ring, instead of a flat disc. All colours derive from the skin's existing body colour. |
| `standalone/JuceLibraryCode/JuceHeader.h`, `plugin/…` | `projectName` changed from `Vial` to `Essential`, which is what the window title reads from |
| `src/interface/editor_sections/*` | remaining user-visible and thread-name strings saying "Vial" now say "Essential" |

## Layout rearrangement (2026-09-22)

Still cosmetic; no synthesis code touched.

| File | Change |
| --- | --- |
| `src/interface/editor_sections/full_interface.cpp` | the tabbed audio sections became a full-width strip across the top with modulation beneath, rather than modulation occupying the right third |
| `src/interface/editor_sections/synthesis_interface.cpp` | oscillators, sample source and both filters laid out side by side as columns |
| `src/interface/editor_sections/oscillator_section.cpp/.h` | each oscillator reads top to bottom as a column; `paintBackground` now follows the placed bounds instead of recomputing the old geometry |
| `src/interface/editor_sections/sample_section.cpp` | same column treatment |
| `src/interface/editor_sections/filter_section.cpp` | response curve on top, two knob rows beneath, source routing along the bottom; cutoff, resonance and blend became knobs |
| `src/interface/editor_sections/modulation_interface.cpp/.h` | envelopes and LFOs side by side at full height instead of stacked in thirds |
| `standalone/builds/osx/Info-App.plist` | added `NSMicrophoneUsageDescription`. JUCE's standalone opens an audio input on launch, and without the key macOS terminates the process outright (`__TCC_CRASHING_DUE_TO_PRIVACY_VIOLATION__`) rather than prompting |

## Rendered dials (2026-09-23)

Cosmetic; the synthesis engine remains untouched.

| File | Change |
| --- | --- |
| `tools/make-assets.py` | **new** — renders the dial and a marble slab from seeded noise. Nothing is downloaded, so no third-party material enters the tree and the look is reproducible from source. |
| `tools/binary_data.py` | **new** — the BinaryData literal/verify helpers, extended to embed binary resources. Every blob is decoded back and compared byte-for-byte before writing, and sizes are patched by matching the symbol, never by assuming the previous value. |
| `tools/embed-assets.py` | **new** — embeds the assets into all three BinaryData copies (standalone, plugin, tests), idempotently. |
| `assets/dial.png`, `assets/marble.jpg` | **new** — generated, not sourced. |
| `*/JuceLibraryCode/BinaryData.{h,cpp}` | two resources added, 157 KB per target. The name/hash tables are deliberately left alone: they must stay length-consistent or `getNamedResourceOriginalFilename` reads past the end of the array, and every access in this codebase is through the extern symbol. |
| `src/interface/editor_components/synth_slider.cpp` | `drawRotaryShadow` composites a rendered dial — black anodised cap, polished chrome collar, baked contact shadow — instead of filling gradients to imply metal. Sized images are cached and built by repeated halving, because JUCE has no mip pyramid and a single 18x minification aliases the chrome ring into noise. The drawn cylinder remains as a fallback if the resource fails to decode. Tick marks removed: beside a rendered dial they read as pen strokes around a photograph. |
| `src/interface/editor_sections/full_interface.cpp` | `redoBackground` can dump the rasterised interface to a PNG when `ESSENTIAL_DUMP_BACKGROUND` is set. The entire static UI is baked into that one image, so visual work can be verified exactly without screen capture, which is unreliable for an OpenGL window. Inert unless the variable is set. |

Only the indicator on a dial of this kind rotates — the collar and cap do not —
so no multi-frame filmstrip is needed. The rotating pointer remains the existing
GPU thumb, and the dial costs nothing per frame: it is baked into the window's
background image alongside the rest of the static interface.

## Marble chassis and light theme (2026-09-23)

Cosmetic; the synthesis engine remains untouched.

| File | Change |
| --- | --- |
| `src/interface/editor_sections/full_interface.cpp/.h` | the window is backed by the generated marble slab instead of a flat fill. `fillBackgroundRegion` is the single path for painting the chassis, and the partial repaints that previously flat-filled `Skin::kBackground` go through it — otherwise a repaint punches a plain rectangle through the stone. The slab is scaled once per background size and cached, since re-resampling it inside a partial repaint would stall the GL lock. |
| `tools/make-skin.py` | regenerated for a light instrument: pale frosted-stone panels, dark type, and displays left dark so luminous traces still read against them. The accent moved from an electric cyan to a deeper azure, which does not vibrate against pale stone. A stale duplicate `GLOBAL` block was also removed — it was shadowing the live one, so palette edits silently did nothing. |
| `default.vitalskin` | regenerated from the above. |

## Supplied slabs, wood fascia, repaint cost (2026-09-23)

Cosmetic and performance; the synthesis engine remains untouched.

| File | Change |
| --- | --- |
| `assets/source/marble.png`, `assets/source/wood.png` | **new** — supplied by the project owner, kept in-tree so the processing is reproducible. |
| `tools/make-assets.py` | the marble is no longer generated; both slabs are scaled and centre-cropped from the supplied sources, so the grain is never distorted. Only the dial is still rendered. |
| `src/interface/editor_components/synth_slider.cpp` | the arc quad and the dial image are clamped to the knob's own cell. The quad is sized in pixels and then normalised, so an arc larger than its cell simply spilled over the knobs either side — which is what was overlapping. |
| `src/interface/editor_sections/full_interface.cpp/.h` | wood fascia behind the macro column and the global control strip, clipped to the body rounding; `repaintChildBackground` restores the chassis under a child and its shadow before repainting, so toggling a section no longer lays shadow over shadow. |
| `tools/make-skin.py` | panel bodies are opaque again — translucency meant every panel fill was an alpha composite over the slab and every partial repaint composited again. The macro and keyboard sections contribute no body so the wood reads through them, with light type since dark ink on walnut is unreadable. A duplicate `"Keyboard"` key in the section map was also removed: two identical keys in one dict literal means the later silently wins, so the fascia styling never applied. |

### Repaint cost

Upstream escalated any synthesis child to repainting the whole strip, because
its oscillators were stacked and shared overlapping shadow regions. This fork's
column layout made that strip the full window width, so toggling one source
re-rasterised all six columns. The sources are disjoint now, so only the
affected column is repainted.

## Marble panels, dark slab, popup contrast (2026-09-23)

| File | Change |
| --- | --- |
| `assets/source/marble_dark.png` | **new** — supplied by the project owner. |
| `src/interface/editor_sections/synth_section.cpp/.h` | `paintBody` samples a marble slab clipped to the body rounding instead of filling a flat colour, offset by the section's position within the painted root so the veining runs continuously beneath the whole instrument rather than restarting in each panel. Effect sections take the dark slab. The slabs are handed to every section at once by `setPanelSlabs`, already scaled to the background image. |
| `src/interface/editor_sections/full_interface.cpp/.h` | scales and supplies both slabs. |
| `src/interface/editor_sections/popup_browser.cpp` | popup rows were tinted with the accent darkened almost to black, which worked when item text was light; on a light instrument the text is dark, so selected rows became dark-on-dark and unreadable. Rows now take a light wash of the accent. Popups also draw their own background colour rather than inheriting `Skin::kBody` from whichever section opened them, which could be transparent or dark. |
| `tools/make-skin.py` | `Body` is a translucent veil over the slab rather than an opaque fill; the ten effect sections invert to a dark veil with light type. |

## Dark panels, effect rack, visible indicator (2026-09-23)

| File | Change |
| --- | --- |
| `src/interface/editor_sections/synth_section.cpp` | every panel takes the dark slab; the light marble stays the chassis they sit on. |
| `src/interface/editor_sections/effects_interface.cpp/.h` | an "add effect" button opens a menu of effects not already in the chain; choosing one enables it through the section's own activator, so the parameter, the order list and the rack stay in step. The rack already showed only enabled effects, so an added effect simply appears. |
| `tools/make-skin.py` | palette inverted for dark panels. The neutral remaps were still carrying light-theme values, so anything a section override routed through them rendered cream on a dark panel. The knob indicator is now the oscillator blue and reaches in across the cap, so a dial is never a blank disc. |

## What was deliberately NOT changed

* Every copyright header. They stay exactly as Matt Tytel wrote them.
* `LICENSE` — GPLv3, unmodified.
* All synthesis, DSP and interface code.
* Upstream's README, kept as `README-upstream.md`.
