#!/usr/bin/env python3
"""
ga_deck_scraper.py — Grand Archive deck scraper (links -> images + decklists)

v4c (clean fix):
- Fixes NameError: img_ref not defined by simplifying resolve_and_download().
- Robust image URL builder (handles full URLs, /cards/images/... paths, and bare filenames).
- 404 fallbacks (toggle rounded param, try without param, swap .jpg/.png).
- Keeps Playwright v4a parsing (clipboard, input_value scraping, JSON sniff) and requests-first.

Your requirements:
- Filenames = card names (duplicates get " (2)", " (3)"...).
- PNG by default (rounded edges).
- Images → E:/Card Game Proxies/Grand Archive/Raw Library (override with --image-library).
- Decklist .txt files written alongside in "Decklists".
- Auto-installs `requests`; auto-installs Playwright + Chromium if needed.
"""
import sys, subprocess, importlib, argparse, json, re, time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# --- bootstrap installs ---
def _pip_install(*pkgs):
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "--no-input", "--user", *pkgs])
def _ensure_on_path_user_site():
    try:
        from site import getusersitepackages
        us = getusersitepackages()
        if isinstance(us, str): us = [us]
        for p in us:
            if p and p not in sys.path:
                sys.path.append(p)
    except Exception:
        pass
def _ensure_requests():
    try:
        import requests  # noqa: F401
    except Exception:
        _pip_install("requests>=2.31.0")
        _ensure_on_path_user_site()
        importlib.invalidate_caches()
def _ensure_playwright():
    try:
        import playwright.sync_api  # noqa: F401
        return True
    except Exception:
        try:
            _pip_install("playwright>=1.46.0")
            _ensure_on_path_user_site()
            importlib.invalidate_caches()
            subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium", "--with-deps"])
            return True
        except Exception:
            return False
_ensure_requests()
import requests

API_SEARCH = "https://api.gatcg.com/cards/search"
HEADERS = {"User-Agent": "GA-Deck-Scraper/3.3c (+local)"}
DEFAULT_IMAGE_LIBRARY = Path("E:/Card Game Proxies/Grand Archive/Raw Library")

# Data classes
@dataclass
class DeckCard:
    section: str
    qty: int
    name: str
@dataclass
class DeckInfo:
    uuid: str
    name: str
    author: Optional[str] = None
    cards: List[DeckCard] = None

# Helpers
def ensure_dir(p: Path): p.mkdir(parents=True, exist_ok=True)
def safe_filename(name: str) -> str:
    s = re.sub(r'[\\/:*?"<>|]+', '_', name).strip()
    return re.sub(r'\s+', ' ', s) or "card"
def read_links(path: Path) -> List[str]:
    if path.is_dir():
        raise SystemExit(f"--links-file points to a directory: {path}. Provide a .txt file of deck URLs.")
    if not path.exists():
        raise SystemExit(f"Links file not found: {path}")
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except PermissionError as e:
        raise SystemExit(f"Can't read links file (permission denied): {path}") from e
    return [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.strip().startswith('#')]

# --- HTML/requests acquisition
def _json_from_next_data(html: str) -> Optional[dict]:
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>', html, re.DOTALL)
    if m:
        try: return json.loads(m.group(1))
        except Exception: pass
    for m in re.finditer(r'<script[^>]+type="application/json"[^>]*>(.+?)</script>', html, re.DOTALL):
        try: return json.loads(m.group(1))
        except Exception: continue
    return None
def _extract_deck_from_possible_json(j: dict) -> Optional['DeckInfo']:
    if not isinstance(j, dict): return None
    cur = j
    for key in ("props","pageProps","deck"):
        if isinstance(cur, dict) and key in cur: cur = cur[key]
        else: break
    if isinstance(cur, dict) and all(k in cur for k in ("name","uuid")):
        main = cur.get("main") or cur.get("mainboard") or []
        material = cur.get("material") or cur.get("material_deck") or []
        cards: List[DeckCard] = []
        for item in main:
            nm = item.get("name") or item.get("card") or item.get("card_name")
            q  = int(item.get("qty") or item.get("quantity") or 1)
            if nm: cards.append(DeckCard(section="Main", qty=q, name=nm))
        for item in material:
            nm = item.get("name") or item.get("card") or item.get("card_name")
            q  = int(item.get("qty") or item.get("quantity") or 1)
            if nm: cards.append(DeckCard(section="Material", qty=q, name=nm))
        return DeckInfo(uuid=str(cur.get("uuid")), name=str(cur.get("name")), author=cur.get("author"), cards=cards)
    if "deck" in j and isinstance(j["deck"], dict):
        d = j["deck"]
        if all(k in d for k in ("name","uuid")):
            main = d.get("main") or d.get("mainboard") or []
            material = d.get("material") or d.get("material_deck") or []
            cards: List[DeckCard] = []
            for item in main:
                nm = item.get("name") or item.get("card") or item.get("card_name")
                q  = int(item.get("qty") or item.get("quantity") or 1)
                if nm: cards.append(DeckCard(section="Main", qty=q, name=nm))
            for item in material:
                nm = item.get("name") or item.get("card") or item.get("card_name")
                q  = int(item.get("qty") or item.get("quantity") or 1)
                if nm: cards.append(DeckCard(section="Material", qty=q, name=nm))
            return DeckInfo(uuid=str(d.get("uuid")), name=str(d.get("name")), author=d.get("author"), cards=cards)
    return None
def harvest_with_requests(url: str, timeout: float = 30.0, verbose: bool=False) -> Optional['DeckInfo']:
    if verbose: print("[debug] requests GET", url)
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    html = r.text
    j = _json_from_next_data(html)
    if j:
        if verbose: print("[debug] found __NEXT_DATA__ json")
        di = _extract_deck_from_possible_json(j)
        if di: return di
    m = re.search(r"window\.__INITIAL_STATE__\s*=\s*(\{.+?\});", html, re.DOTALL)
    if m:
        try:
            if verbose: print("[debug] found window.__INITIAL_STATE__ json")
            di = _extract_deck_from_possible_json(json.loads(m.group(1)))
            if di: return di
        except Exception as e:
            if verbose: print("[debug] parse __INITIAL_STATE__ failed:", e)
    return None

# --- Playwright fallback (v4a feature set)
def _deck_from_generic_json(url: str, title: Optional[str], author: Optional[str], obj: Any, verbose: bool=False) -> Optional['DeckInfo']:
    def walk(node):
        if isinstance(node, dict):
            if "cards" in node and isinstance(node["cards"], list):
                return node["cards"]
            if "main" in node and isinstance(node["main"], list): return node["main"]
            if "mainboard" in node and isinstance(node["mainboard"], list): return node["mainboard"]
            for v in node.values():
                r = walk(v)
                if r is not None: return r
        elif isinstance(node, list):
            good = []
            for it in node:
                if isinstance(it, dict) and "name" in it and any(k in it for k in ("qty","quantity","count","amount","quantity_in_deck")):
                    good.append(it)
            if len(good) >= 5:
                return good
            for it in node:
                r = walk(it)
                if r is not None: return r
        return None
    cards_raw = walk(obj)
    if not cards_raw: return None
    cards: List[DeckCard] = []
    for it in cards_raw:
        name = str(it.get("name") or it.get("card") or it.get("card_name") or "").strip()
        if not name: continue
        qty = it.get("qty", it.get("quantity", it.get("count", it.get("amount", it.get("quantity_in_deck", 1)))))
        try: qty = int(qty)
        except Exception: qty = 1
        cards.append(DeckCard(section="Main", qty=qty, name=name))
    if not cards: return None
    uuid = url.rstrip('/').split('/')[-1]
    return DeckInfo(uuid=uuid, name=title or "Deck", author=author, cards=cards)

def _parse_text_export_to_deck(url: str, title: str, author: Optional[str], text: str) -> Optional['DeckInfo']:
    if not text or len(text.strip()) < 3: return None
    lines = [ln.strip() for ln in text.splitlines()]
    cards: List[DeckCard] = []
    pat = re.compile(r'^\s*(\d+)\s*(?:[xX]\s*)?(.+?)\s*$')
    for ln in lines:
        m = pat.match(ln)
        if not m: continue
        qty = int(m.group(1))
        name = m.group(2).strip()
        if len(name) < 2: continue
        if name.lower().startswith(("side", "material", "main", "total")): 
            continue
        cards.append(DeckCard(section="Main", qty=qty, name=name))
    if not cards: return None
    uuid = url.rstrip('/').split('/')[-1]
    return DeckInfo(uuid=uuid, name=title or "Deck", author=author, cards=cards)

def harvest_with_playwright(url: str, timeout: float = 90.0, verbose: bool=False) -> Optional['DeckInfo']:
    ok = _ensure_playwright()
    if not ok:
        if verbose: print("[debug] playwright not available")
        return None
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(user_agent=HEADERS["User-Agent"])
        try:
            context.grant_permissions(["clipboard-read", "clipboard-write"], origin="https://shoutatyourdecks.com")
        except Exception:
            pass
        page = context.new_page()

        title = None
        author = None
        deck_found: Optional[DeckInfo] = None
        candidate_jsons: List[Any] = []
        candidate_texts: List[str] = []

        def on_response(resp):
            nonlocal deck_found
            try:
                ct = resp.headers.get("content-type","")
                if "application/json" in ct:
                    data = resp.json()
                    candidate_jsons.append(data)
                    di = _extract_deck_from_possible_json(data) or _deck_from_generic_json(url, title, author, data, verbose=verbose)
                    if di and not deck_found:
                        deck_found = di
                        if verbose: print("[debug] network JSON looked like a deck:", resp.url)
            except Exception:
                pass
        page.on("response", on_response)

        if verbose: print("[debug] playwright goto", url)
        page.goto(url, wait_until="networkidle", timeout=int(timeout*1000))

        try:
            title_el = page.locator("h1, h2, h3").first
            if title_el and title_el.count() > 0:
                title = title_el.inner_text().strip()
        except Exception:
            pass

        if deck_found:
            context.close(); browser.close(); return deck_found

        def try_click(label_regex: str):
            try:
                page.get_by_role("button", name=re.compile(label_regex, re.I)).first.click(timeout=2500)
                if verbose: print(f"[debug] clicked {label_regex}")
                page.wait_for_timeout(250)
                return True
            except Exception:
                try:
                    page.get_by_text(re.compile(label_regex, re.I)).first.click(timeout=2500)
                    if verbose: print(f"[debug] clicked {label_regex}")
                    page.wait_for_timeout(250)
                    return True
                except Exception:
                    return False
        for nm in ("View","Stats","Export","Share","Text","Omnidex","Silvie","Copy"):
            try_click(nm)

        try:
            clip = page.evaluate("async () => await navigator.clipboard.readText()")
            if isinstance(clip, str) and len(clip.strip()) > 5:
                candidate_texts.append(clip.strip())
                if verbose: print("[debug] got clipboard text")
        except Exception:
            pass

        def gather_texts():
            sels = [
                "textarea", "input[type='text']",
                "pre", "code",
                "[contenteditable='true']", ".cm-content", ".cm-content *",
                "div[role=dialog] textarea", "div[role=dialog] pre", "div[role=dialog] code"
            ]
            for sel in sels:
                try:
                    loc = page.locator(sel)
                    n = loc.count()
                    for i in range(min(n, 12)):
                        el = loc.nth(i)
                        try:
                            val = el.input_value()
                        except Exception:
                            val = None
                        if isinstance(val, str) and len(val.strip()) > 5:
                            candidate_texts.append(val.strip())
                        try:
                            t = el.inner_text().strip()
                            if len(t) > 5:
                                candidate_texts.append(t)
                        except Exception:
                            pass
                except Exception:
                    continue
        gather_texts()

        try:
            all_text = page.evaluate("document.body.innerText")
            if isinstance(all_text, str) and len(all_text) > 20:
                candidate_texts.append(all_text)
        except Exception:
            pass

        seen = set(); uniq_texts = []
        for t in candidate_texts:
            k = t.strip()
            if k not in seen:
                uniq_texts.append(k); seen.add(k)

        for t in uniq_texts:
            di = _parse_text_export_to_deck(url, title or "Deck", author, t)
            if di:
                deck_found = di
                if verbose: print("[debug] parsed deck from text candidates")
                break

        if not deck_found:
            for obj in candidate_jsons:
                di = _deck_from_generic_json(url, title, author, obj, verbose=verbose)
                if di:
                    deck_found = di
                    if verbose: print("[debug] parsed deck from stored JSON candidates")
                    break

        context.close(); browser.close()
        return deck_found

# --- GA API + images
def search_card(name: str) -> Optional[dict]:
    params = {"name": name, "page_size": 5, "separate_editions": False, "order": "ASC", "sort": "collector_number"}
    r = requests.get(API_SEARCH, params=params, headers=HEADERS, timeout=30)
    if r.status_code == 404: return None
    r.raise_for_status()
    data = r.json()
    results = (data or {}).get("data") or []
    if not results: return None
    lower = name.lower()
    for c in results:
        if str(c.get("name","")).lower() == lower:
            return c
    return results[0]

def choose_edition(card: dict) -> Optional[dict]:
    eds = (card or {}).get("editions") or []
    if not eds: return None
    en = [e for e in eds if ((e.get("set") or {}).get("language") == "EN")]
    pool = en if en else eds
    def rel(e): return ((e.get("set") or {}).get("release_date")) or "9999-99-99"
    pool.sort(key=rel)
    return pool[0]

# Robust image URL handling
def build_image_url(image_ref: str) -> str:
    if not image_ref:
        return ""
    s = str(image_ref).strip()
    if s.startswith("http://") or s.startswith("https://"):
        return s
    s = s.lstrip("/")
    if s.startswith("cards/images/"):
        return "https://api.gatcg.com/" + s
    return "https://api.gatcg.com/cards/images/" + s

def download_image(image_ref: str, out_path: Path, rounded_png: bool = True, verbose: bool=False):
    """
    Download with robust URL building and simple 404 fallbacks:
      1) rounded=true/false depending on request
      2) no rounded param
      3) swap extension .jpg <-> .png and retry with rounded param
    """
    url = build_image_url(image_ref)
    if not url:
        raise ValueError("Empty image reference")
    ensure_dir(out_path.parent)

    def _try(url, params):
        r = requests.get(url, params=params, headers=HEADERS, stream=True, timeout=60)
        if r.status_code == 404:
            raise FileNotFoundError("404")
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024*256):
                if chunk:
                    f.write(chunk)

    # attempt 1: rounded flag
    try:
        _try(url, {"rounded": "true" if rounded_png else "false"})
        return
    except FileNotFoundError:
        # attempt 2: no rounded
        try:
            _try(url, None)
            return
        except FileNotFoundError:
            # attempt 3: swap extension
            if url.lower().endswith(".jpg"):
                alt = url[:-4] + ".png"
            elif url.lower().endswith(".png"):
                alt = url[:-4] + ".jpg"
            else:
                raise
            _try(alt, {"rounded": "true" if rounded_png else "false"})

def write_deck_txt(deck, decklists_root: Path):
    counts: Dict[str, int] = {}
    for c in deck.cards:
        counts[c.name] = counts.get(c.name, 0) + int(c.qty)
    lines = [
        "Grand Archive Decklist",
        f"Name: {deck.name}",
        f"UUID: {deck.uuid}",
        f"Author: {deck.author or 'Unknown'}",
        f"Exported: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        f"Total cards: {sum(counts.values())}",
        ""
    ]
    for name in sorted(counts.keys(), key=lambda s: s.lower()):
        lines.append(f"{counts[name]}x {name}")
    ensure_dir(decklists_root)
    out_path = decklists_root / f"{safe_filename(deck.name)} [{deck.uuid}].txt"
    out_path.write_text("\n".join(lines), encoding='utf-8')

def resolve_and_download(deck, image_library: Path, rounded_png: bool = True, verbose: bool=False) -> Tuple[int,int]:
    """
    Unified implementation: define img_ref exactly once per card name,
    then write qty copies (suffixing " (n)" for duplicates).
    """
    ensure_dir(image_library)
    downloaded = failed = 0

    # Aggregate by card name
    counts: Dict[str, int] = {}
    for c in deck.cards:
        counts[c.name] = counts.get(c.name, 0) + int(c.qty)

    for name, qty in sorted(counts.items(), key=lambda kv: kv[0].lower()):
        card = search_card(name)
        if not card: 
            print(f"[warn] Not found in GA API: {name}"); failed += qty; continue
        ed = choose_edition(card)
        if not ed:
            print(f"[warn] No editions for: {name}"); failed += qty; continue

        # Choose best image ref once
        img_ref = ed.get("image") or ed.get("image_url")
        if not img_ref:
            imgs = ed.get("images") or []
            if isinstance(imgs, list) and imgs:
                img_ref = imgs[0].get("image") or imgs[0].get("url")
        if not img_ref:
            img_ref = ((ed.get("slug") or "image") + ".jpg")

        base = safe_filename(name)
        copies = max(1, qty)
        for i in range(copies):
            suffix = "" if copies == 1 else f" ({i+1})"
            ext = ".png" if rounded_png else ".jpg"
            out_path = image_library / f"{base}{suffix}{ext}"
            try:
                download_image(img_ref, out_path, rounded_png=rounded_png, verbose=verbose)
                downloaded += 1
            except Exception as e:
                print(f"[error] download failed for {name}{suffix}: {e}")
                failed += 1

    return downloaded, failed

def main():
    ap = argparse.ArgumentParser(description="Parse GA deck links, download PNG images named as card names, and export TXT decklists (requests + playwright fallback).")
    ap.add_argument("--links-file", required=True, help="Path to a text file of deck URLs (one per line).")
    ap.add_argument("--image-library", default=str(DEFAULT_IMAGE_LIBRARY), help="Folder to place all card images.")
    ap.add_argument("--png", choices=["true","false"], default="true", help="Download PNG (rounded=true). Default true.")
    ap.add_argument("--decklists-root", help="Folder to write TXT decklists. Default: '<parent of image-library>/Decklists'")
    ap.add_argument("--verbose", action="store_true", help="Print extra debugging output.")
    args = ap.parse_args()

    links_path = Path(args.links_file).expanduser()
    image_library = Path(args.image_library).expanduser()
    rounded_png = (args.png.lower() == "true")
    verbose = args.verbose

    decklists_root = Path(args.decklists_root).expanduser() if args.decklists_root else (image_library.parent if image_library.parent != image_library else Path.cwd()) / "Decklists"
    ensure_dir(image_library); ensure_dir(decklists_root)

    urls = read_links(links_path)
    if not urls:
        print("No URLs found in links file."); return

    total_decks = total_downloaded = total_failed = 0
    failed_decks = []
    for url in urls:
        print(f"\n=== Processing deck: {url} ===")
        deck = None
        try:
            deck = harvest_with_requests(url, verbose=verbose)
        except Exception as e:
            print(f"[warn] requests acquisition error: {e}")
        if not deck:
            print("[info] Falling back to headless browser (v4c)...")
            deck = harvest_with_playwright(url, verbose=verbose)
        if not deck or not deck.cards:
            print(f"[warn] Could not extract deck from {url}")
            failed_decks.append(url); continue
        print(f"[ok] {deck.name} by {deck.author or 'Unknown'} — {sum(c.qty for c in deck.cards)} cards (pre-aggregation)")
        total_decks += 1
        write_deck_txt(deck, decklists_root)
        d, f = resolve_and_download(deck, image_library=image_library, rounded_png=rounded_png, verbose=verbose)
        total_downloaded += d; total_failed += f

    print("\n=== Summary ===")
    print(f"Decks parsed:       {total_decks}/{len(urls)}")
    print(f"Images downloaded:  {total_downloaded}")
    print(f"Image failures:     {total_failed}")
    if failed_decks:
        print("Decks that failed to parse:")
        for u in failed_decks: print("  -", u)

if __name__ == "__main__":
    main()
