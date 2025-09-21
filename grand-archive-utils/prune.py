# save as prune_by_full_arts.py
import argparse
from pathlib import Path

def main():
    ap = argparse.ArgumentParser(description="Delete files in PRUNE_DIR if their names match files in KEEP_DIR (non-recursive).")
    ap.add_argument("--keep-dir", required=True, help=r'Folder to KEEP (e.g. "E:\Card Game Proxies\Grand Archive\Raw Library\Full Arts")')
    ap.add_argument("--prune-dir", required=True, help=r'Folder to PRUNE (e.g. "E:\Card Game Proxies\Grand Archive\Raw Library")')
    ap.add_argument("--match", choices=["stem", "name"], default="stem",
                    help='Match on filename stem (no extension, default) or full name (with extension).')
    ap.add_argument("--dry-run", action="store_true", help="Show what would be deleted without changing anything.")
    args = ap.parse_args()

    keep_dir = Path(args.keep_dir)
    prune_dir = Path(args.prune_dir)

    if not keep_dir.is_dir():
        raise SystemExit(f"KEEP_DIR not found or not a directory: {keep_dir}")
    if not prune_dir.is_dir():
        raise SystemExit(f"PRUNE_DIR not found or not a directory: {prune_dir}")
    if keep_dir.resolve() == prune_dir.resolve():
        raise SystemExit("KEEP_DIR and PRUNE_DIR must be different directories.")

    # Build set of names from keep_dir (non-recursive)
    keep_set = set()
    for p in keep_dir.iterdir():
        if p.is_file():
            key = (p.stem if args.match == "stem" else p.name).lower()
            keep_set.add(key)

    # Plan deletions in prune_dir (non-recursive)
    to_delete = []
    for p in prune_dir.iterdir():
        if p.is_file():
            key = (p.stem if args.match == "stem" else p.name).lower()
            if key in keep_set:
                to_delete.append(p)

    print(f"Found {len(to_delete)} file(s) in {prune_dir} that match names in {keep_dir}:")
    for f in to_delete:
        print(f"  DELETE: {f.name}")

    if args.dry_run:
        print("\n--dry-run enabled, no changes made.")
        return

    # Execute
    deleted = 0
    for f in to_delete:
        try:
            f.unlink()
            deleted += 1
        except Exception as e:
            print(f"[error] delete failed {f}: {e}")

    print(f"\nDone. Deleted {deleted} file(s).")

if __name__ == "__main__":
    main()
