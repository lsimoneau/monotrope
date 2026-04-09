#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "python-frontmatter",
# ]
# ///
"""Enrich book reviews with ISBN and cover images from OpenLibrary."""

import json
import sys
import time
import urllib.request
import urllib.parse
from pathlib import Path

import frontmatter

REVIEWS_DIR = Path(__file__).parent / "site" / "content" / "reviews"
COVERS_DIR = Path(__file__).parent / "site" / "static" / "covers"

OL_SEARCH = "https://openlibrary.org/search.json"
OL_COVER = "https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"


def search_isbn(title: str, author: str) -> str | None:
    """Search OpenLibrary for an ISBN by title and author."""
    params = {"title": title, "author": author, "limit": "3", "fields": "isbn"}
    url = f"{OL_SEARCH}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "monotrope-enrich/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
    for doc in data.get("docs", []):
        for isbn in doc.get("isbn", []):
            if len(isbn) == 13:
                return isbn
    # fall back to ISBN-10 if no 13
    for doc in data.get("docs", []):
        for isbn in doc.get("isbn", []):
            if len(isbn) == 10:
                return isbn
    return None


def fetch_cover(isbn: str, dest: Path) -> bool:
    """Download a cover image for the given ISBN. Returns True on success."""
    url = OL_COVER.format(isbn=isbn)
    req = urllib.request.Request(url, headers={"User-Agent": "monotrope-enrich/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = resp.read()
    # OpenLibrary returns a tiny 1x1 placeholder when no cover exists
    if len(data) < 1000:
        return False
    dest.write_bytes(data)
    return True


def enrich(path: Path, dry_run: bool = False) -> None:
    """Enrich a single review file with ISBN and cover."""
    post = frontmatter.load(path)
    title = post.get("title", "")
    author = post.get("book_author", "")

    has_isbn = bool(post.get("isbn"))
    has_cover = bool(post.get("cover"))

    if has_isbn and has_cover:
        print(f"  skip  {path.name} (already enriched)")
        return

    # ── ISBN lookup ──────────────────────────────────
    isbn = post.get("isbn", "")
    if not isbn:
        print(f"  search  title={title!r} author={author!r}")
        isbn = search_isbn(title, author)
        if not isbn:
            print(f"  ✗  no ISBN found for {path.name}")
            return
        print(f"  found  ISBN {isbn}")

    # ── Cover download ──────────────────────────────
    slug = path.stem
    cover_file = COVERS_DIR / f"{slug}.jpg"
    if not has_cover and not cover_file.exists():
        print(f"  fetch  cover → {cover_file.relative_to(Path(__file__).parent)}")
        if not dry_run:
            COVERS_DIR.mkdir(parents=True, exist_ok=True)
            if not fetch_cover(isbn, cover_file):
                print(f"  ✗  no cover image available for ISBN {isbn}")
                cover_file = None
        else:
            cover_file = None
    elif cover_file.exists():
        print(f"  ok  cover already exists")

    # ── Update frontmatter ──────────────────────────
    changed = False
    if not has_isbn:
        post["isbn"] = isbn
        changed = True
    if not has_cover and cover_file and cover_file.exists():
        post["cover"] = f"/covers/{slug}.jpg"
        changed = True

    if changed and not dry_run:
        path.write_text(frontmatter.dumps(post) + "\n")
        print(f"  ✓  updated {path.name}")
    elif changed:
        print(f"  (dry run) would update {path.name}")


def main() -> None:
    dry_run = "--dry-run" in sys.argv

    reviews = sorted(REVIEWS_DIR.glob("*.md"))
    reviews = [r for r in reviews if r.name != "_index.md"]

    if not reviews:
        print("No reviews found.")
        return

    print(f"Enriching {len(reviews)} review(s)...\n")
    for path in reviews:
        print(f"  ── {path.stem} ──")
        try:
            enrich(path, dry_run=dry_run)
        except Exception as e:
            print(f"  ✗  error: {e}")
        print()


if __name__ == "__main__":
    main()
