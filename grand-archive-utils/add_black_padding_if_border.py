# save as add_black_padding_if_border.py
import argparse, sys, subprocess, importlib
from pathlib import Path

def _ensure_pillow():
    try:
        import PIL  # noqa: F401
    except Exception:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "pillow"])
        importlib.invalidate_caches()

_ensure_pillow()
from PIL import Image

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}

def is_black_border(img: Image.Image, sample: int = 3, threshold: int = 16, tolerance: float = 0.98) -> bool:
    """Return True if the outer border strip is (almost) all black."""
    if img.mode not in ("RGB","RGBA","L"):
        img = img.convert("RGB")
    w, h = img.size
    sample = max(1, min(sample, w//2, h//2))
    px = img.convert("RGB").load()

    def is_black_rgb(r,g,b): return r <= threshold and g <= threshold and b <= threshold

    total = 0
    black = 0
    # top & bottom
    for y in range(0, sample):
        for x in range(w):
            r,g,b = px[x,y]; total += 1; black += is_black_rgb(r,g,b)
    for y in range(h - sample, h):
        for x in range(w):
            r,g,b = px[x,y]; total += 1; black += is_black_rgb(r,g,b)
    # left & right (exclude already-counted top/bottom rows)
    for x in range(0, sample):
        for y in range(sample, h - sample):
            r,g,b = px[x,y]; total += 1; black += is_black_rgb(r,g,b)
    for x in range(w - sample, w):
        for y in range(sample, h - sample):
            r,g,b = px[x,y]; total += 1; black += is_black_rgb(r,g,b)

    return total > 0 and (black / total) >= tolerance

def add_padding(img: Image.Image, pad: int = 75) -> Image.Image:
    w, h = img.size
    mode = "RGBA" if img.mode == "RGBA" else "RGB"
    bg = (0, 0, 0, 255) if mode == "RGBA" else (0, 0, 0)
    canvas = Image.new(mode, (w + 2*pad, h + 2*pad), bg)
    canvas.paste(img, (pad, pad))
    return canvas

def process_path(path: Path, recursive: bool, pad: int, sample: int, threshold: int, tolerance: float, out_dir: Path|None, dry_run: bool):
    targets = []
    if path.is_file():
        targets = [path]
    elif path.is_dir():
        targets = list((path.rglob("*") if recursive else path.iterdir()))
    else:
        print(f"[warn] Not found: {path}")
        return

    # filter to images (top-level files only if not recursive)
    files = [p for p in targets if p.is_file() and p.suffix.lower() in IMAGE_EXTS]

    changed = 0
    for p in files:
        try:
            with Image.open(p) as img:
                if is_black_border(img, sample=sample, threshold=threshold, tolerance=tolerance):
                    out = (out_dir / p.name) if out_dir else p
                    print(f"[ok] Border is black → add {pad}px: {p.name}")
                    if not dry_run:
                        padded = add_padding(img, pad=pad)
                        out.parent.mkdir(parents=True, exist_ok=True)
                        # Preserve format when possible (fallback to PNG if unknown)
                        fmt = img.format if img.format in ("PNG","JPEG","WEBP","BMP","TIFF") else None
                        if fmt:
                            padded.save(out, format=fmt)
                        else:
                            padded.save(out.with_suffix(".png"))
                    changed += 1
                else:
                    print(f"[skip] Border not black: {p.name}")
        except Exception as e:
            print(f"[error] {p}: {e}")

    print(f"\nDone. Updated {changed} / {len(files)} image(s).")

def main():
    ap = argparse.ArgumentParser(description="Add 75 black px to all sides if the existing border is black.")
    ap.add_argument("path", help=r'File or folder, e.g. "E:\Card Game Proxies\Grand Archive\Raw Library"')
    ap.add_argument("--padding", type=int, default=75, help="Padding in pixels on each side (default 75)")
    ap.add_argument("--sample", type=int, default=3, help="Width of edge strip to test (default 3px)")
    ap.add_argument("--threshold", type=int, default=16, help="RGB max value to consider a pixel black (default 16)")
    ap.add_argument("--tolerance", type=float, default=0.98, help="Fraction of edge pixels that must be black (default 0.98)")
    ap.add_argument("--recursive", action="store_true", help="Process subfolders too (default: off)")
    ap.add_argument("--out-dir", help="Optional output folder (otherwise overwrites in place)")
    ap.add_argument("--dry-run", action="store_true", help="Show what would change without writing files")
    args = ap.parse_args()

    path = Path(args.path)
    out_dir = Path(args.out_dir).resolve() if args.out_dir else None
    process_path(
        path=path,
        recursive=args.recursive,
        pad=args.padding,
        sample=args.sample,
        threshold=args.threshold,
        tolerance=args.tolerance,
        out_dir=out_dir,
        dry_run=args.dry_run,
    )

if __name__ == "__main__":
    main()
