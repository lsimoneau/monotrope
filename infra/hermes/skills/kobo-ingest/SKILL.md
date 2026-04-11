---
name: kobo-ingest
description: Download and import Kobo ebook purchases into the calibre library
version: 1.0.0
platforms: [linux]
metadata:
  hermes:
    tags: [books, kobo, calibre]
    category: library
    requires_toolsets: []
    config: []
---
# Kobo Book Ingestion

## When to Use
- When the user asks to download a book from Kobo
- When a forwarded Kobo purchase receipt email arrives
- When the user asks to check for new Kobo purchases

## Procedure

### From a receipt email
1. Parse the email to extract the book title(s) and author(s)
2. For each book:
   a. Use `mcp_calibre_search_library` to check if the book already exists in the library — if it does, skip it and tell the user
   b. Use `mcp_calibre_list_kobo_books` to find the book's product ID — match by title/author from the receipt
   c. Use `mcp_calibre_download_book` with the product ID to download the epub
   d. Use `mcp_calibre_import_to_library` with the downloaded filename to add it to calibre
   e. Verify the import by searching the library again

### From a manual request (e.g. "download [book title]")
1. Use `mcp_calibre_list_kobo_books` to find the book
2. Use `mcp_calibre_search_library` to check it's not already imported
3. Download and import as above

## Pitfalls
- Never use bulk download — always download one book at a time by product ID
- Multi-book orders: receipts may contain multiple books, process each separately
- Title matching is fuzzy — the receipt title may not exactly match the Kobo product listing, use your judgement
- If a book doesn't appear in `list_kobo_books` yet, it may not have synced — wait a few minutes and try once more
- Always confirm the import succeeded by searching the library after importing

## Verification
After importing, search the library for the book title. Report the result to the user with title, author, and confirmation it's in the library.
