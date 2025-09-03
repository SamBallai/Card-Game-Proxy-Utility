# Card-Game-Proxy-Utility
Tools for building printable proxies and color-correcting assets across multiple card games.

- **`copy_deck_images_general.py`** – Copies card images into per-deck folders from a single image library using pitch-aware matching, resume-safe copying, and smart back pairing.  
- **`BatchColorMatch.jsx`** – Photoshop automation that color-matches “Upscaled Images” to “Original Images” using your recorded action, saving corrected results.

---

## Table of Contents

- [copy_deck_images_general.py](#copy_deck_images_generalpy)
  - [Highlights](#highlights)
  - [Requirements](#requirements)
  - [Decklist format](#decklist-format)
  - [Folder naming](#folder-naming)
  - [Back images (front/back, double-faced, tokens)](#back-images-frontback-doublefaced-tokens)
  - [Installation](#installation)
  - [Usage](#usage)
  - [Examples](#examples)
  - [Errors & logs](#errors--logs)
- [BatchColorMatch.jsx](#batchcolormatchjsx)
  - [What it does](#what-it-does)
  - [Requirements](#requirements-1)
  - [Folder layout](#folder-layout)
  - [Set up your Photoshop Action](#set-up-your-photoshop-action)
  - [Run the script](#run-the-script)
  - [Behavior details](#behavior-details)
  - [Troubleshooting](#troubleshooting)
- [License](#license)

---

## `copy_deck_images_general.py`

### Highlights

- **Single images root**: works with one consolidated image library (recursive).  
- **Pitch-aware**: matches `Card Name (red|yellow|blue)` strictly to the right color variant.  
- **Smart matching**: exact key → no ambiguity; fallback still respects color.  
- **Resume-safe**: re-runs skip files already copied (`[SKIP-EXISTS]`).  
- **Re-run-friendly folders**: reuses existing deck folders; only creates a *variant* if a different deck would collide **in the same run**.  
- **Smart back pairing**:
  - Finds explicit `(... (Back))` files.  
  - Infers backs that *reference the front* in parentheses (e.g., `Inner Chi (Pass Over Marvel)` as back of `Pass Over (Marvel)`).  
  - Optional **override map** `--backs-map` for tricky cases.  
  - If any backs were copied, deck folder is suffixed with **`- Unique front and backs`**.
- **Progress bars** (via `rich`) + readable logs.

### Requirements

- **Python** 3.8+  
- (Optional) [`rich`](https://pypi.org/project/rich/) for progress UI – the script will auto-install if missing.
- Your image library can include: `.png .jpg .jpeg .webp .tif .tiff`

### Decklist format

Plain text with one card per line in **`Nx Card Name`** form. Pitch is optional:

```
Title: Imported Deck
Deck: Aurora, Shooting Star
Game: Flesh and Blood
Side: Runner   # optional

Aurora, Shooting Star

Deck
3x Bolt'n' Shot (red)
3x Bolt'n' Shot (yellow)
2x Fealty Token (Marvel)
```

Anything not in `Nx Something` format will be ignored (headers are fine). The script normalizes `(yel)` → `(yellow)`, `(blu)` → `(blue)`.

### Folder naming

Output folder name uses (in order) the first available of:
- `Identity/Hero/Commander` (if `--by-identity`), else
- `Deck:` header, else
- `Title:`, else
- filename stem.

You can override with `--name-template`, e.g.:
```
--name-template "{game} - {side} - {deck}"
```

### Back images (front/back, double-faced, tokens)

The script tries, in order:

1) **Explicit** back names like `Card Name (Back)` or `Card Name (red) (Back)`  
2) **Override map**: provide `--backs-map path\to\backs_map.csv` with lines:
   ```
   Pass Over (Marvel),Inner Chi (Pass Over Marvel)
   Fealty Token (Marvel),Fealty Token (Marvel) (Back)
   ```
3) **Inference**: images whose parentheses mention the front (e.g., `Inner Chi (Pass Over Marvel)`).
4) **Keyword**: filenames containing `back` and the front’s tokens.

When a back is found, the script copies **one back art per front type** and the **same quantity** (e.g., `3x`).

### Installation

```bash
# optional but recommended: create a venv
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell
pip install rich          # optional; script can auto-install
```

### Usage

```
py copy_deck_images_general.py ^
  --images "E:\Card Game Proxies\All Games\Images" ^
  --decks  "E:\Card Game Proxies\Decklists" ^
  --output "E:\Card Game Proxies\Built" ^
  --game "Android Netrunner" ^
  --by-identity ^
  --backs-map "E:\Card Game Proxies\backs_map.csv"
```

**Common flags**

- `--images` **(required)**: root of all card images (searches recursively)
- `--decks` **(required)**: folder with your decklist `.txt` files
- `--output`: where to create per-deck folders (default: `--decks`)
- `--by-identity`: prefer identity/hero/commander names over file stems
- `--name-template`: e.g. `"{game} - {side} - {deck}"`
- `--recursive-decks`: search decklists recursively
- `--exts`: customize allowed image extensions
- `--backs-map`: CSV or `front,back` pairs to force back matches
- `--no-progress`: disable progress bars

### Examples

**Minimal**
```bash
py copy_deck_images_general.py --images "D:\Proxies\Images" --decks "D:\Proxies\Decklists"
```

**With naming template & identity**
```bash
py copy_deck_images_general.py ^
  --images "D:\Proxies\Images" ^
  --decks  "D:\Proxies\Decklists" ^
  --output "D:\Proxies\Output" ^
  --game "Flesh and Blood" ^
  --by-identity ^
  --name-template "{game} - {deck}"
```

**Windows paths with spaces**
```bash
py copy_deck_images_general.py --images "E:\Card Game Proxies\Android Netrunner\Completed Local Library" --decks "E:\Card Game Proxies\Android Netrunner\Decklists"
```

### Errors & logs

- An `ERRORS.txt` file is written to the output root.  
  - `[MISSING]` – no source image found for a card  
  - `[SKIP-EXISTS]` – destination already present (resume-safe)  
  - `[AMBIGUOUS]` – multiple candidates (fallback only; exact matches don’t warn)  
  - `[COPY-ERROR]` – file copy failed  
- If any backs were copied, the deck folder is auto-renamed with **`- Unique front and backs`**.

---

## `BatchColorMatch.jsx`

### What it does

Automates Photoshop to **match color** from **Original Images** (reference) to **Upscaled Images** (targets) and saves corrected outputs to **Result**—one image at a time—using your recorded Photoshop Action.

### Requirements

- **Adobe Photoshop** (CC recommended)  
- Your own **Action** that performs the “Match Color” (or equivalent) step **using the currently open reference document**.  
- File types: `.png .jpg .jpeg .tif .tiff .psd`

### Folder layout

Select a **project root** when the script starts. Inside it, create:

```
<Project Root>/
  Original Images/   # reference, correct color
  Upscaled Images/   # target, needs correction
  Result/            # output (auto-created)
```

> The script matches by **basename (case-insensitive)** and **ignores** trailing ` - x of y` suffixes (e.g., `Card Name - 2 of 3.png`).

### Set up your Photoshop Action

- Record an action (e.g., **`Default Actions / MatchColorFromRef`**) that:
  1. Assumes the **target** document is active.
  2. Uses **Match Color** (or your preferred adjustment) with **Source: current open reference document** (don’t hard-code a filename).
  3. Applies and returns to the active target.

Update these two lines in the script if your action is named differently:
```js
var ACTION_SET  = "Default Actions";
var ACTION_NAME = "MatchColorFromRef";
```

### Run the script

1. In Photoshop: **File → Scripts → Browse…**  
2. Pick `BatchColorMatch.jsx`.  
3. Choose your **Project Root**.  
4. The script opens pairs, runs your action, and writes PNGs into `Result/`.  
5. A log is saved to `Result/BatchColorMatch.log`.

### Behavior details

- **Matching**: by basename only; ignores copy suffixes and extensions.  
- **Preference** among duplicate refs: PSD → TIFF → PNG → JPEG.  
- **Saving**: PNG by default (change `savePNG` if you prefer TIFF/JPEG).  
- **Safety**: opens both files, runs action, saves result, closes without modifying originals.  
- **Log** includes processed, missing refs, and failed files.

### Troubleshooting

- **“Missing folder” alerts** → Ensure the three folders are named exactly as above.  
- **Action doesn’t find the source** → Re-record the action with “Source: [document]” and no hard-coded filename.  
- **Color/ICC issues** → Add a `Convert to Profile` or `Assign Profile` step in your action before Match Color.  
- **Save format** → Swap `savePNG` to a TIFF/JPEG saver if you need different output.

---

## License

CC-BY-NC-SA
