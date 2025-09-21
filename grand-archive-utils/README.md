Prune
-------------------------------------
Builds a set of filenames from Full Arts
Deletes any file in Raw Library whose name (stem, case-insensitive) matches one in Full Arts
Doesn’t touch subfolders

# Preview only (no changes)
python .\prune.py `
  --keep-dir "E:\Card Game Proxies\Grand Archive\Raw Library\Full Arts" `
  --prune-dir "E:\Card Game Proxies\Grand Archive\Raw Library" `
  --dry-run

# Do it for real
python .\prune.py `
  --keep-dir "E:\Card Game Proxies\Grand Archive\Raw Library\Full Arts" `
  --prune-dir "E:\Card Game Proxies\Grand Archive\Raw Library"


Junk Removal
---------------------------
Gets rid of the " - academy-guide-p24-cpr" part

# Preview (no changes)
python .\junk_removal.py "E:\Card Game Proxies\Grand Archive\Raw Library" --dry-run

# Do it for real (recursively)
python .\junk_removal.py "E:\Card Game Proxies\Grand Archive\Raw Library"

# If a clean name already exists, add " (2)" etc. (default). To overwrite instead:
python .\junk_removal.py "E:\Card Game Proxies\Grand Archive\Raw Library" --on-conflict overwrite

# Only top-level folder, no subfolders
python .\junk_removal.py "E:\Card Game Proxies\Grand Archive\Raw Library" --no-recursive


Image Dedupe
-------------------------
Deletes all duplicates of an image marked with (2), (3), etc. Only the (1) or images without a number in parenthesis will be kept. Rename all images with numbers in parenthesis to remove the number

# Preview what it will do (no changes)
python .\image_dedupe.py "E:\Card Game Proxies\Grand Archive\Raw Library" --dry-run

# Do it for real (recursive across subfolders)
python .\image_dedupe.py "E:\Card Game Proxies\Grand Archive\Raw Library"

# Only the top-level folder, no subfolders
python .\image_dedupe.py "E:\Card Game Proxies\Grand Archive\Raw Library" --no-recursive


add_black_padding_if_border
--------------------------------------------------
Checks the outer edge (a thin strip) for black pixels
If ≥98% of the strip is black (tolerance), it expands canvas by 75 px on each side with black and pastes the image in the middle
If some borders are very dark but not pure black, you can relax detection a bit:
    raise --threshold (e.g., 24),
    or lower --tolerance (e.g., 0.95),
    or increase the strip --sample to 5–8 px.

# Preview only (no changes), non-recursive
python .\add_black_padding_if_border.py "E:\Card Game Proxies\Grand Archive\Raw Library" --dry-run

# Do it for real, non-recursive (default)
python .\add_black_padding_if_border.py "E:\Card Game Proxies\Grand Archive\Raw Library"

# Include subfolders
python .\add_black_padding_if_border.py "E:\Card Game Proxies\Grand Archive\Raw Library" --recursive

# Write results to a separate folder
python .\add_black_padding_if_border.py "E:\Card Game Proxies\Grand Archive\Raw Library" --out-dir "E:\Card Game Proxies\Grand Archive\Bordered"
