# Essential

**Essential is a fork of [Vital](https://github.com/mtytel/vital), a spectral
warping wavetable synthesiser created by Matt Tytel.**

All of the synthesis engine and interface work here is his. This fork exists
only to build and distribute the GPLv3 source under a name that does not use
his trademarks, as his licence terms require. If you want the real thing, with
presets, support and a wavetable editor that talks to his service, get it from
[vital.audio](https://vital.audio) — and consider paying for it.

Upstream's own README is preserved as [README-upstream.md](README-upstream.md).

## Licence

**GPLv3**, inherited from upstream and unchanged — see [LICENSE](LICENSE).

That is not a formality. It means:

* Any binary you distribute must come with this source, under the GPLv3.
* You cannot relicense it, and you cannot fold this code into a closed-source
  or proprietary app.
* **You cannot ship it on the iOS App Store.** The App Store terms and the
  GPLv3 contradict each other, and upstream states this explicitly. The only
  route to an App Store build is a paid licensing exception from
  licensing@vital.audio.
* You cannot use the names "Vital", "Vital Audio", "Tytel" or "Matt Tytel" to
  market or name a build. Hence "Essential".
* The presets bundled with the free version of Vital are under a separate
  licence and are not redistributable. None are included here.

## Changes from upstream

See [CHANGES-FORK.md](CHANGES-FORK.md) for the itemised list with dates, as
GPLv3 section 5(a) requires. In summary: renamed the product and its data
directories, changed the bundle identifier and company name, and compiled out
the account/authentication code so builds never contact vital.audio.

No synthesis, DSP or interface code has been altered.

## Building (macOS)

```bash
xcodebuild -project standalone/builds/osx/Essential.xcodeproj \
           -target "Essential - App" -configuration Release build
```

The app lands in `standalone/builds/osx/build/Release/Essential.app`. It is a
universal binary (arm64 + x86_64) and is unsigned, so the first launch needs
right-click → Open, or `xattr -dr com.apple.quarantine Essential.app`.

Linux builds use the `Makefile`; Windows uses the Visual Studio projects under
`standalone/builds/vs19`. Both are upstream's and untouched.

## This is a desktop synthesiser

Vital is C++ and JUCE, built for desktop plugin formats. There is an iOS target
in `plugin/builds/iOS` for AUv3, but the GPLv3 blocks App Store distribution,
so it is not a route to a phone app. A mobile synth needs a mobile codebase.
