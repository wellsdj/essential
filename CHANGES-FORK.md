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

## What was deliberately NOT changed

* Every copyright header. They stay exactly as Matt Tytel wrote them.
* `LICENSE` — GPLv3, unmodified.
* All synthesis, DSP and interface code.
* Upstream's README, kept as `README-upstream.md`.
