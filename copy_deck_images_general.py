#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
copy_deck_images_general.py
Pitch-safe, resume-safe, smart backs, and re-run friendly folders.

Folders:
- If the target folder already exists when the script starts, reuse it (no variant).
- Only create a "(variant N)" during THIS run if a *different deck* collides on the same target name.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------- Optional progress UI ----------
def _ensure_package(pkg: str, import_name: Optional[str] = None) -> bool:
    mod = import_name or pkg
    try:
        __import__(mod)
        return True
    except Exception:
        pass
    try:
        print(f"[setup] Installing: {pkg} ...")
        subprocess.check_call([sys.executable, "-m", "pip", "install",
                               "--disable-pip-version-check", "--quiet", pkg])
        __import__(mod)
        print(f"[setup] Installed: {pkg}")
        return True
    except Exception as e:
        print(f"[setup] Failed to install {pkg}: {e}")
        return False

HAVE_RICH = _ensure_package("rich")
if HAVE_RICH:
    try:
        from rich.console import Console
        from rich.progress import (
            Progress, BarColumn, TextColumn, TimeElapsedColumn,
            TimeRemainingColumn, SpinnerColumn
        )
    except Exception:
        HAVE_RICH = False

# ---------- CLI ----------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Copy deck images into per-deck folders (pitch-safe, resume-safe, smart backs).")
    p.add_argument("--images", required=True, type=Path, help="Root containing ALL card images (recursive).")
    p.add_argument("--decks", required=True, type=Path, help="Directory containing decklist .txt files.")
    p.add_argument("--output", type=Path, help="Where per-deck folders are created (default: --decks).")
    p.add_argument("--exts", nargs="*", default=[".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"],
                   help="Image extensions.")
    p.add_argument("--game", type=str, default="", help="Game label for folder naming (optional).")
    p.add_argument("--by-identity", action="store_true", help="Prefer Identity/Hero/Commander over filename for deck name.")
    p.add_argument("--name-template", type=str, default="", help="Folder template using {game},{side},{deck},{file}.")
    p.add_argument("--recursive-decks", action="store_true", help="Also read decklists from subfolders.")
    p.add_argument("--backs-map", type=Path, help="CSV or text with lines 'front,back' for explicit back pairings.")
    p.add_argument("--no-progress", action="store_true", help="Disable progress UI.")
    return p.parse_args()

# ---------- Logging / utils ----------
def log(msg: str, error_log: Path) -> None:
    error_log.parent.mkdir(parents=True, exist_ok=True)
    with error_log.open("a", encoding="utf-8") as f:
        f.write(msg.rstrip() + "\n")
    if HAVE_RICH:
        Console().log(msg)
    else:
        print(msg)

def sanitize_filename(name: str) -> str:
    name = name.replace(":", "_")
    for ch in '<>:"/\\|?*':
        name = name.replace(ch, "")
    return re.sub(r"\s+", " ", name).strip().rstrip(".")

def normalize_key(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())

def tokenize(s: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", s.lower())

# Pitch helpers
def extract_pitch(name: str) -> Optional[str]:
    m = re.search(r"\((red|yellow|blue|yel|blu)\)\s*$", name, flags=re.IGNORECASE)
    if not m:
        return None
    w = m.group(1).lower()
    return {"yel": "yellow", "blu": "blue"}.get(w, w)

def strip_pitch_suffix(name: str) -> str:
    return re.sub(r"\s*\((?:red|yellow|blue|yel|blu)\)\s*$", "", name, flags=re.IGNORECASE).strip()

def strip_back_suffix(name: str) -> str:
    return re.sub(r"\s*\(back\)\s*$", "", name, flags=re.IGNORECASE).strip()

# ---------- Index images ----------
def index_library(images_root: Path, exts: List[str], error_log: Path) -> Tuple[Dict[str, List[Path]], List[Path]]:
    index: Dict[str, List[Path]] = {}
    catalog: List[Path] = []
    if not images_root.exists():
        log(f"[ERROR] Images directory not found: {images_root}", error_log)
        return index, catalog
    for ext in exts:
        for p in images_root.rglob(f"*{ext}"):
            catalog.append(p)
            key = normalize_key(p.stem)
            if key:
                index.setdefault(key, []).append(p)
    ext_order = {e.lower(): i for i, e in enumerate(exts)}
    for k, paths in index.items():
        paths.sort(key=lambda x: (ext_order.get(x.suffix.lower(), 999), str(x).lower()))
    return index, catalog

# ---------- Matching (pitch-aware) ----------
def best_match(card_name: str, index: Dict[str, List[Path]]) -> Tuple[Optional[Path], List[Path], bool]:
    pitch = extract_pitch(card_name)
    key = normalize_key(card_name)
    if key in index:
        return index[key][0], index[key], True  # exact

    base = strip_pitch_suffix(card_name) if pitch else card_name
    base_key = normalize_key(base)
    candidates_keys = [k for k in index.keys() if k.startswith(base_key) or base_key.startswith(k)]
    candidates: List[Path] = []
    for ck in candidates_keys:
        candidates.extend(index[ck])

    if pitch:
        pkw = pitch
        candidates = [p for p in candidates if re.search(rf"\b{pkw}\b", p.stem.lower())]

    if candidates:
        return candidates[0], candidates, False

    # Very loose
    rb_key = normalize_key(strip_back_suffix(strip_pitch_suffix(card_name)))
    loose = []
    for k, v in index.items():
        if rb_key and (k.startswith(rb_key) or rb_key.startswith(k)):
            loose.extend(v)
    if loose:
        return loose[0], loose, False

    return None, [], False

# ---------- Back pairing ----------
def load_backs_map(path: Optional[Path]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    if not path or not path.exists():
        return mapping
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in re.split(r",\s*", line, maxsplit=1)]
        if len(parts) == 2 and parts[0] and parts[1]:
            mapping[parts[0]] = parts[1]
    return mapping

BACK_CACHE: Dict[str, List[Path]] = {}

def find_back_images(front_card: str, src: Path, index: Dict[str, List[Path]],
                     catalog: List[Path], backs_map: Dict[str, str]) -> List[Path]:
    cache_key = normalize_key(front_card)
    if cache_key in BACK_CACHE:
        return BACK_CACHE[cache_key]

    results: List[Path] = []
    pitch = extract_pitch(front_card)
    base = strip_back_suffix(strip_pitch_suffix(front_card))

    # 1) Explicit (Back)
    for name in filter(None, [
        f"{base} (Back)",
        f"{base} ({pitch}) (Back)" if pitch else None,
        f"{strip_back_suffix(strip_pitch_suffix(src.stem))} (Back)",
    ]):
        k = normalize_key(name)
        if k in index:
            results.extend(index[k])

    # 2) Map override
    if not results:
        for key in (front_card, base):
            if key in backs_map:
                k = normalize_key(backs_map[key])
                if k in index:
                    results.extend(index[k])
                    break

    # 3) Inferred via parentheses mention
    if not results:
        base_tokens = set(tokenize(base))
        if base_tokens:
            for p in catalog:
                for grp in re.findall(r"\(([^)]{2,})\)", p.stem):
                    if base_tokens.issubset(set(tokenize(grp))):
                        results.append(p)
                        break

    # 4) 'back' keyword + token containment
    if not results:
        base_tokens = set(tokenize(base))
        for p in catalog:
            sl = p.stem.lower()
            if "back" in sl and base_tokens.issubset(set(tokenize(sl))):
                results.append(p)

    # Dedup
    seen = set()
    deduped: List[Path] = []
    for p in results:
        key = (p.stem, p.suffix.lower())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(p)

    BACK_CACHE[cache_key] = deduped
    return deduped

# ---------- Deck parsing ----------
HEADER_KEYS = {
    "title": re.compile(r"^\s*title\s*:\s*(.+)$", re.IGNORECASE),
    "identity": re.compile(r"^\s*identity\s*:\s*(.+)$", re.IGNORECASE),
    "deck": re.compile(r"^\s*deck\s*:\s*(.+)$", re.IGNORECASE),
    "hero": re.compile(r"^\s*hero\s*:\s*(.+)$", re.IGNORECASE),
    "commander": re.compile(r"^\s*commander\s*:\s*(.+)$", re.IGNORECASE),
    "side": re.compile(r"^\s*(side|faction)\s*:\s*(.+)$", re.IGNORECASE),
    "game": re.compile(r"^\s*game\s*:\s*(.+)$", re.IGNORECASE),
}
PAT_COUNT_X_NAME = re.compile(r"^\s*(\d+)\s*[xX]\s+(.+?)\s*$")

def parse_deck_file(path: Path, prefer_identity: bool) -> Tuple[str, str, str, List[Tuple[int, str]]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = [ln.rstrip() for ln in text.splitlines()]

    title = identity = deck_name = hero = commander = side = game = ""
    entries: List[Tuple[int, str]] = []

    for ln in lines[:100]:
        for key, pat in HEADER_KEYS.items():
            m = pat.match(ln)
            if not m:
                continue
            if key == "title": title = m.group(1).strip()
            elif key == "identity": identity = m.group(1).strip()
            elif key == "deck": deck_name = m.group(1).strip()
            elif key == "hero": hero = m.group(1).strip()
            elif key == "commander": commander = m.group(1).strip()
            elif key == "side": side = m.group(2).strip()
            elif key == "game": game = m.group(1).strip()

    candidates = [
        identity if prefer_identity else "",
        hero if prefer_identity else "",
        commander if prefer_identity else "",
        deck_name,
        title,
        path.stem,
    ]
    deck_display = next((c for c in candidates if c), path.stem)

    for ln in lines:
        m = PAT_COUNT_X_NAME.match(ln.strip())
        if m:
            cnt = int(m.group(1))
            nm  = m.group(2).strip()
            pitch = extract_pitch(nm)
            if pitch:
                nm = strip_pitch_suffix(nm) + f" ({pitch})"
            entries.append((cnt, nm))
    return deck_display, side, game, entries

# ---------- Folder naming ----------
def compose_folder_base(deck_display: str, side: str, game_cli: str, game_header: str,
                        filename_stem: str, name_template: str) -> str:
    game = (game_header or game_cli).strip()
    deck = deck_display.strip()
    side = side.strip()
    file_stem = filename_stem.strip()
    if name_template:
        return name_template.format(game=game, side=side, deck=deck, file=file_stem)
    if game and side: return f"{game} - {side} - {deck}"
    if game and not side: return f"{game} - {deck}"
    if side and not game: return f"{side} - {deck}"
    return deck

def choose_dest_dir(base_dir: Path, base_name: str, deck_key: str,
                    existing_dirs_start: set[str], folder_claims: Dict[str, str],
                    error_log: Path) -> Path:
    """
    Re-run friendly folder creation:
    - If `base_name` existed when we started, reuse it (no variant).
    - Else, if another deck in THIS run already claimed `base_name` with a different deck_key,
      create "(variant N)" for the current deck.
    - Else, create `base_name`.
    """
    base_name = sanitize_filename(base_name)
    target = base_dir / base_name

    # Reuse existing folders (from previous runs) without creating variants.
    if base_name in existing_dirs_start or target.exists():
        target.mkdir(parents=True, exist_ok=True)
        folder_claims.setdefault(base_name, deck_key)
        return target

    # Check for same-run collisions
    if base_name in folder_claims and folder_claims[base_name] != deck_key:
        n = 2
        while True:
            variant = sanitize_filename(f"{base_name} (variant {n})")
            vpath = base_dir / variant
            if not vpath.exists() and variant not in folder_claims:
                vpath.mkdir(parents=True, exist_ok=True)
                folder_claims[variant] = deck_key
                log(f"[VARIANT] '{base_name}' already claimed by '{folder_claims[base_name]}'. "
                    f"Created '{variant}' for '{deck_key}'.", error_log)
                return vpath
            n += 1

    # Fresh create and claim
    target.mkdir(parents=True, exist_ok=True)
    folder_claims[base_name] = deck_key
    return target

def rename_with_suffix(dest_dir: Path, suffix: str, error_log: Path) -> Path:
    parent = dest_dir.parent
    base = dest_dir.name
    if base.endswith(suffix):
        return dest_dir
    new_name = sanitize_filename(f"{base} {suffix}")
    new_path = parent / new_name
    if not new_path.exists():
        try:
            dest_dir.rename(new_path)
            return new_path
        except Exception as e:
            log(f"[RENAME-ERROR] {dest_dir.name} -> {new_name} :: {e}", error_log)
            return dest_dir
    # Variant if that exact suffix name exists
    n = 2
    while True:
        candidate = parent / sanitize_filename(f"{new_name} (variant {n})")
        if not candidate.exists():
            try:
                dest_dir.rename(candidate)
                return candidate
            except Exception as e:
                log(f"[RENAME-ERROR] {dest_dir.name} -> {candidate.name} :: {e}", error_log)
                return dest_dir
        n += 1

# ---------- Main ----------
def main() -> None:
    args = parse_args()
    images_root: Path = args.images
    decks_root: Path = args.decks
    output_root: Path = args.output or decks_root
    error_log: Path = output_root / "ERRORS.txt"

    exts = [e.lower() for e in args.exts]
    index, catalog = index_library(images_root, exts, error_log)
    backs_map = load_backs_map(args.backs_map)

    # Decklists
    if args.recursive_decks:
        deck_files = sorted(p for p in decks_root.rglob("*.txt") if p.is_file())
    else:
        deck_files = sorted(p for p in decks_root.glob("*.txt") if p.is_file())
    if not deck_files:
        print(f"No decklists found in: {decks_root}")
        return

    # Snapshot existing output folders at start (re-run friendly)
    existing_dirs_start = {p.name for p in output_root.iterdir() if p.is_dir()} if output_root.exists() else set()
    folder_claims: Dict[str, str] = {}  # name -> deck_key for this run

    def handle_deck(deck_path: Path, progress=None, decks_task_id=None) -> None:
        deck_display, side, game_header, entries = parse_deck_file(deck_path, prefer_identity=args.by_identity)
        if not entries:
            log(f"[WARN] No cards parsed from {deck_path.name}; skipping.", error_log)
            if HAVE_RICH and (not args.no_progress) and progress and decks_task_id is not None:
                progress.update(decks_task_id, advance=1)
            return

        folder_base = compose_folder_base(deck_display, side, args.game, game_header, deck_path.stem, args.name_template)
        deck_key = deck_display  # used to decide "different deck" during the same run
        dest_dir = choose_dest_dir(output_root, folder_base, deck_key, existing_dirs_start, folder_claims, error_log)

        total_copies = sum(qty for qty, _ in entries)
        unique_back_used = False

        if HAVE_RICH and (not args.no_progress) and progress is not None:
            deck_task_id = progress.add_task(f"[bold]{dest_dir.name}[/] — Preparing...", total=total_copies)
        else:
            deck_task_id = None
            print(f"\n=== {dest_dir.name} === ({total_copies} copies)")

        for qty, card in entries:
            src, candidates, is_exact = best_match(card, index)
            if not src:
                log(f"[MISSING] {deck_path.name} | {card} (x{qty}) not found under {images_root}", error_log)
                if HAVE_RICH and (not args.no_progress) and progress is not None and deck_task_id is not None:
                    progress.update(deck_task_id, advance=qty, description=f"{dest_dir.name} — Missing: {card} (x{qty})")
                continue

            # Copy N times (resume-safe)
            for i in range(1, qty + 1):
                out_name = f"{sanitize_filename(card)} - {i} of {qty}{src.suffix.lower()}"
                out_path = dest_dir / out_name
                if out_path.exists():
                    log(f"[SKIP-EXISTS] {deck_path.name} | {out_path.name}", error_log)
                else:
                    try:
                        shutil.copy2(src, out_path)
                    except Exception as e:
                        log(f"[COPY-ERROR] {deck_path.name} | {card} -> {out_path.name} :: {e}", error_log)

                if HAVE_RICH and (not args.no_progress) and progress is not None and deck_task_id is not None:
                    progress.update(deck_task_id, advance=1, description=f"{dest_dir.name} — {card} ({i}/{qty})")

            if (not is_exact) and len(candidates) > 1:
                sample = ", ".join(c.name for c in candidates[:3])
                log(f"[AMBIGUOUS] {deck_path.name} | {card} matched multiple files; used '{src.name}'. Candidates: {sample}", error_log)

            # Backs
            backs = find_back_images(card, src, index, catalog, backs_map)
            if backs:
                unique_back_used = True
                base_req = strip_back_suffix(strip_pitch_suffix(card))
                back_path = backs[0]  # one back art per card type
                for i in range(1, qty + 1):
                    out_name_b = f"{sanitize_filename(base_req)} (Back) - {i} of {qty}{back_path.suffix.lower()}"
                    out_path_b = dest_dir / out_name_b
                    if out_path_b.exists():
                        log(f"[SKIP-EXISTS] {deck_path.name} | {out_path_b.name}", error_log)
                    else:
                        try:
                            shutil.copy2(back_path, out_path_b)
                        except Exception as e:
                            log(f"[COPY-ERROR] {deck_path.name} | {base_req} (Back) -> {out_path_b.name} :: {e}", error_log)

        if unique_back_used:
            rename_with_suffix(dest_dir, " - Unique front and backs", error_log)

        if HAVE_RICH and (not args.no_progress) and progress is not None and decks_task_id is not None:
            progress.update(decks_task_id, advance=1)

    # Progress orchestration
    if HAVE_RICH and (not args.no_progress):
        columns = [
            TextColumn("{task.description}"),
            BarColumn(bar_width=None),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            TextColumn("•"),
            TimeRemainingColumn(),
            TextColumn("  "),
            SpinnerColumn(),
        ]
        with Progress(*columns, transient=False) as progress:
            decks_task = progress.add_task(f"[bold]All Decks[/] — Scanning", total=len(deck_files))
            for deck_path in deck_files:
                handle_deck(deck_path, progress=progress, decks_task_id=decks_task)
            progress.update(decks_task, description="[bold]All Decks[/] — Done")
    else:
        print(f"Found {len(deck_files)} decklists. Output -> {output_root}")
        processed = 0
        for deck_path in deck_files:
            processed += 1
            print(f"\n[{processed}/{len(deck_files)}] {deck_path.name}")
            handle_deck(deck_path, progress=None, decks_task_id=None)

    print("\nDone. Check ERRORS.txt for details.")

if __name__ == "__main__":
    main()
