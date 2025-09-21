# save as dedupe_images.py
import argparse, re
from pathlib import Path

NUM_RE = re.compile(r"^(?P<base>.+?)\s\((?P<num>\d+)\)$", re.IGNORECASE)
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}

def plan_actions(root: Path, recursive: bool):
    files = (root.rglob("*") if recursive else root.iterdir())
    groups = {}  # key = (base_name, ext)  e.g. ("Card Name", ".png")
    for p in files:
        if not p.is_file():
            continue
        ext = p.suffix.lower()
        if ext not in IMAGE_EXTS:
            continue
        stem = p.stem  # filename without extension
        m = NUM_RE.match(stem)
        if m:
            base = m.group("base")
            num = int(m.group("num"))
        else:
            base = stem
            num = 0  # unnumbered
        key = (base, ext)
        groups.setdefault(key, {"plain": None, "one": None, "dupes": []})
        if num == 0:
            groups[key]["plain"] = p
        elif num == 1:
            groups[key]["one"] = p
        else:
            groups[key]["dupes"].append(p)

    deletes, renames = [], []
    for (base, ext), info in groups.items():
        plain, one, dupes = info["plain"], info["one"], info["dupes"]

        # Always delete (2), (3), ...
        for d in dupes:
            deletes.append(d)

        # If an unnumbered file exists, keep it and delete (1) if present.
        if plain is not None:
            if one is not None:
                deletes.append(one)
            continue

        # Otherwise, if (1) exists, rename it to unnumbered.
        if one is not None:
            target = one.with_name(f"{base}{ext}")
            # Avoid accidental overwrite if something appeared meanwhile
            if target.exists() and target.resolve() != one.resolve():
                # if target exists but is same file, skip; else delete target first
                deletes.append(target)
            renames.append((one, target))

    return renames, deletes

def main():
    ap = argparse.ArgumentParser(description="Delete numbered duplicate images and normalize (1) → unnumbered.")
    ap.add_argument("folder", help="Folder to process (e.g., E:\\Card Game Proxies\\Grand Archive\\Raw Library)")
    ap.add_argument("--no-recursive", action="store_true", help="Do not process subfolders")
    ap.add_argument("--dry-run", action="store_true", help="Show what would happen without changing anything")
    args = ap.parse_args()

    root = Path(args.folder)
    if not root.exists():
        raise SystemExit(f"Folder not found: {root}")

    renames, deletes = plan_actions(root, recursive=not args.no_recursive)

    print(f"Planned renames: {len(renames)}")
    for src, dst in renames:
        print(f"  RENAME: {src}  ->  {dst}")
    print(f"Planned deletions: {len(deletes)}")
    for d in deletes:
        print(f"  DELETE: {d}")

    if args.dry_run:
        print("\n--dry-run enabled, no changes made.")
        return

    # Execute
    for src, dst in renames:
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            src.rename(dst)
        except Exception as e:
            print(f"[error] rename failed {src} -> {dst}: {e}")

    for d in deletes:
        try:
            d.unlink()
        except Exception as e:
            print(f"[error] delete failed {d}: {e}")

    print("\nDone.")

if __name__ == "__main__":
    main()
