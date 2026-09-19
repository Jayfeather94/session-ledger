# Third-party licenses

The built program bundles the components below. Their license texts are
reproduced here as those licenses require.

| Component | Used for | License | Text |
|---|---|---|---|
| PySide6 / Qt 6 | the whole UI | LGPL v3 | `LGPL-3.0.txt` |
| Pillow | background images (JPEG/WebP decode, smooth scaling) | MIT-CMU (HPND) | `Pillow-MIT-CMU.txt` |

`GPL-3.0.txt` is included as well: LGPL v3 is written as a set of additional
permissions on top of GPL v3 and incorporates it by reference, so the two
belong together.

## Relinking (why this build satisfies the LGPL)

The LGPL requires that a user be able to replace the covered library with a
modified version of their own.

This build is a PyInstaller **onedir** bundle, not a single-file executable.
The Qt libraries are ordinary `.dll` files sitting in
`_internal\PySide6\` next to the program, loaded at run time — they are not
packed inside `SessionLedger.exe`. To run against your own build of Qt,
replace the `.dll` files in that folder.

## Upstream sources

- PySide6 — https://code.qt.io/cgit/pyside/pyside-setup.git/
- Qt 6 — https://code.qt.io/cgit/qt/
- Pillow — https://github.com/python-pillow/Pillow

The LGPL and GPL texts were taken verbatim from
https://www.gnu.org/licenses/ ; the Pillow text ships inside the Pillow wheel.
