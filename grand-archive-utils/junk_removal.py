# save as trim_slug_suffix.py
import argparse, re
from pathlib import Path

# Match the *last* " - slug" before the extension, e.g. "Name - anything.not.dots.jpg" -> "Name" + ".jpg"
PATTERN = re.compile(r"^(?P<base>.+)\s-\s[^.]+(?P<ext>\.[^.]+)$")

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".tif", ".tiff"}

def target_name(p: Path) -> Path | None:
    stem, ext = p.stem, p.suffix
    m = PATTERN.match(stem + ext)
    if not m:
        return None
    base = m.group("base").strip()
    if not base:
        return None
    return p.with_name(f"{base}{m.group('ext')}")

def uniquify(path: Path) -> Path:
    """If path exists, append ' (2)', ' (3)', ... before the extension."""
    if not path.exists():
        return path
    base, ext = path.stem, path.suffix
    i = 2
    while True:
        cand = path.with_name(f"{base} ({i}){ext}")
        if not cand.exists():
            return cand
        i += 1

def main():
    ap = argparse.ArgumentParser(description="Trim trailing ' - slug' from image filenames.")
    ap.add_argument("folder", help="Folder to process (e.g., E:\\Card Game Proxies\\Grand Archive\\Raw Library)")
    ap.add_argument("--no-recursive", action="store_true", help="Do not process subfolders")
    ap.add_argument("--dry-run", action="store_true", help="Show actions without renaming")
    ap.add_argument("--exts", nargs="*", help="Whitelist of extensions (default common image types)")
    ap.add_argument("--on-conflict", choices=["suffix", "overwrite", "skip"], default="suffix",
                    help="When target name exists: add numeric suffix (default), overwrite, or skip")
    args = ap.parse_args()

    root = Path(args.folder)
    if not root.exists():
        raise SystemExit(f"Folder not found: {root}")

    exts = {e.lower() if e.startswith(".") else f".{e.lower()}" for e in (args.exts or IMAGE_EXTS)}
    files = (root.rglob("*") if not args.no_recursive else root.iterdir())

    renames = []
    for p in files:
        if not p.is_file():
            continue
        if p.suffix.lower() not in exts:
            continue
        tgt = target_name(p)
        if not tgt or tgt.name == p.name:
            continue  # no change needed
        # handle conflicts
        final_tgt = tgt
        if tgt.exists():
            if args.on_conflict == "skip":
                continue
            elif args.on_conflict == "overwrite":
                pass  # will rename over it
            else:  # suffix
                final_tgt = uniquify(tgt)
        renames.append((p, final_tgt))

    print(f"Found {len(renames)} file(s) to rename.")
    for src, dst in renames:
        print(f"  RENAME: {src.name}  ->  {dst.name}")

    if args.dry_run:
        print("\n--dry-run enabled, no changes made.")
        return

    for src, dst in renames:
        try:
            src.rename(dst)
        except Exception as e:
            print(f"[error] rename failed {src} -> {dst}: {e}")

    print("\nDone.")

if __name__ == "__main__":
    main()
