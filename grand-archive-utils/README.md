# Grand Archive Image & Deck Utilities

A small collection of one-off Python helpers for organizing and cleaning a Grand Archive proxy/image library.

> Targets Windows/PowerShell paths in the examples below, but the scripts are plain Python and work cross-platform.

---

## Prune

Removes base images from `Raw Library` when a **Full Art** version of the same card name exists.

**What it does**

- Builds a set of filenames from **Full Arts**
- Deletes any file in **Raw Library** whose **name stem** (case-insensitive, ignoring extension) matches one in **Full Arts**
- Non-recursive (top-level only)

**Usage**

```powershell
# Preview only (no changes)
python .\prune.py \
  --keep-dir "E:\Card Game Proxies\Grand Archive\Raw Library\Full Arts" \
  --prune-dir "E:\Card Game Proxies\Grand Archive\Raw Library" \
  --dry-run

# Do it for real
python .\prune.py \
  --keep-dir "E:\Card Game Proxies\Grand Archive\Raw Library\Full Arts" \
  --prune-dir "E:\Card Game Proxies\Grand Archive\Raw Library"
```

---

## Junk Removal

Trims the trailing slug after `" - "` in filenames, e.g.  
`Academy Guide - academy-guide-p24-cpr.jpg` → `Academy Guide.jpg`.

**Usage**

```powershell
# Preview (no changes)
python .\junk_removal.py "E:\Card Game Proxies\Grand Archive\Raw Library" --dry-run

# Do it for real (recursively)
python .\junk_removal.py "E:\Card Game Proxies\Grand Archive\Raw Library"

# If a clean name already exists, add " (2)" etc. (default). To overwrite instead:
python .\junk_removal.py "E:\Card Game Proxies\Grand Archive\Raw Library" --on-conflict overwrite

# Only top-level folder, no subfolders
python .\junk_removal.py "E:\Card Game Proxies\Grand Archive\Raw Library" --no-recursive
```

---

## Image Dedupe

Normalizes numbered duplicates:

- Keeps either `Name.png` **or** `Name (1).png`
- Deletes `Name (2).png`, `Name (3).png`, …  
- If only `Name (1).png` exists, it’s renamed to `Name.png`

**Usage**

```powershell
# Preview what it will do (no changes)
python .\image_dedupe.py "E:\Card Game Proxies\Grand Archive\Raw Library" --dry-run

# Do it for real (recursive across subfolders)
python .\image_dedupe.py "E:\Card Game Proxies\Grand Archive\Raw Library"

# Only the top-level folder, no subfolders
python .\image_dedupe.py "E:\Card Game Proxies\Grand Archive\Raw Library" --no-recursive
```

---

## Add Black Padding (conditional)

Adds a **75-px black border** to all sides **only if** the existing border is already (nearly) black.

**Details**

- Samples a thin outer strip; if ≥98% of pixels are below a black threshold, expands canvas by 75 px on each edge
- Tunable detection if borders are very dark but not pure black:
  - Increase `--threshold` (e.g., `24`)
  - Lower `--tolerance` (e.g., `0.95`)
  - Increase edge `--sample` (e.g., `5–8` px)

**Usage**

```powershell
# Preview only (no changes), non-recursive
python .\add_black_padding_if_border.py "E:\Card Game Proxies\Grand Archive\Raw Library" --dry-run

# Do it for real, non-recursive (default)
python .\add_black_padding_if_border.py "E:\Card Game Proxies\Grand Archive\Raw Library"

# Include subfolders
python .\add_black_padding_if_border.py "E:\Card Game Proxies\Grand Archive\Raw Library" --recursive

# Write results to a separate folder
python .\add_black_padding_if_border.py "E:\Card Game Proxies\Grand Archive\Raw Library" --out-dir "E:\Card Game Proxies\Grand Archive\Bordered"
```

---

## Notes

- All scripts are designed to be cautious: most have a `--dry-run` mode.
- Paths above use Windows style; on macOS/Linux, adjust paths and remove PowerShell line-continuations (`` ` ``).
