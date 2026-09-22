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

## What was deliberately NOT changed

* Every copyright header. They stay exactly as Matt Tytel wrote them.
* `LICENSE` — GPLv3, unmodified.
* All synthesis, DSP and interface code.
* Upstream's README, kept as `README-upstream.md`.
