"""MCP server exposing calibre-web library and kobodl tools."""

import json
import subprocess
from pathlib import Path

from mcp.server.fastmcp import FastMCP

LIBRARY_PATH = "/library"
DOWNLOADS_PATH = "/downloads"
KOBODL_CONFIG = "/home/config/kobodl.json"
CALIBRE_CONFIG_DIR = "/config/calibre"

mcp = FastMCP("calibre", host="0.0.0.0", port=8000)


def _run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120, **kwargs)


@mcp.tool()
def search_library(query: str) -> str:
    """Search the calibre library by title or author. Use this to check if a book already exists before importing."""
    result = _run([
        "calibredb", "list",
        "--with-library", LIBRARY_PATH,
        "--search", query,
        "--fields", "title,authors",
        "--line-width", "0",
    ], env={"CALIBRE_CONFIG_DIRECTORY": CALIBRE_CONFIG_DIR})
    if result.returncode != 0:
        return f"Error: {result.stderr.strip()}"
    return result.stdout.strip() or "No matching books found."


@mcp.tool()
def list_kobo_books() -> str:
    """List all books available for download from the Kobo account."""
    result = _run([
        "kobodl", "--config", KOBODL_CONFIG,
        "book", "list",
    ])
    if result.returncode != 0:
        return f"Error: {result.stderr.strip()}"
    return result.stdout.strip() or "No books found."


@mcp.tool()
def download_book(book_id: str) -> str:
    """Download a single book from Kobo by its product ID. Returns the filename on success."""
    result = _run([
        "kobodl", "--config", KOBODL_CONFIG,
        "book", "get",
        "--book-id", book_id,
        "--output-dir", DOWNLOADS_PATH,
    ], timeout=300)
    if result.returncode != 0:
        return f"Error: {result.stderr.strip()}"
    # Find the most recently created epub in downloads
    epubs = sorted(Path(DOWNLOADS_PATH).glob("*.epub"), key=lambda p: p.stat().st_mtime, reverse=True)
    if epubs:
        return f"Downloaded: {epubs[0].name}"
    return "Download completed but no epub file found. Check the output:\n" + result.stdout.strip()


@mcp.tool()
def import_to_library(filename: str) -> str:
    """Import an epub file from the downloads directory into the calibre library."""
    filepath = Path(DOWNLOADS_PATH) / filename
    if not filepath.exists():
        return f"Error: {filepath} does not exist."
    if not filepath.suffix.lower() == ".epub":
        return f"Error: {filepath} is not an epub file."
    result = _run([
        "calibredb", "add", str(filepath),
        "--with-library", LIBRARY_PATH,
    ], env={"CALIBRE_CONFIG_DIRECTORY": CALIBRE_CONFIG_DIR})
    if result.returncode != 0:
        return f"Error: {result.stderr.strip()}"
    return result.stdout.strip() or f"Imported {filename} successfully."


def main():
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
