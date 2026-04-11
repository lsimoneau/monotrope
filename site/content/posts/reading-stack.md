---
title: "Building a Self-Hosted Reading Stack"
date: 2026-04-11
draft: true
---

I wanted reading stats. Detailed ones — pages read per day, time spent reading, which books I abandoned halfway through. Kobo has some of this, but it's locked in their cloud, surfaced through a mediocre app, and could disappear any time they decide to pivot or shut down.

That one desire — "I want to own my reading data" — ended up pulling on a thread that led to a whole self-hosted reading infrastructure. Here's what I ended up with and how it all fits together.

## The starting point: Kobo + DRM

I read on a Kobo Libra 2. The hardware is great, but the software ecosystem is firmly in Rakuten's walled garden. Books you buy are locked with DRM, and your reading data lives on Kobo's servers.

The first step was getting my books out. [kobodl](https://github.com/subdavis/kobodl) handles this — it authenticates with your Kobo account, downloads your purchased EPUBs, and strips the DRM. It also has a small web UI for managing the process, and a CLI for automation.

I run it as a Docker container on my server, with the web UI bound only to my WireGuard interface so it's not publicly accessible. A sync script downloads any new purchases and feeds them into the next piece of the stack.

## Library management: calibre-web

[calibre-web](https://github.com/janeczku/calibre-web) is a web frontend for a Calibre library. It gives you a browsable, searchable catalogue of your books with the ability to download in various formats. Think of it as your personal library management system.

The integration with kobodl is straightforward: kobodl downloads EPUBs into a shared Docker volume, and a sync script imports them into the Calibre library using `calibredb add`. The script is idempotent — kobodl keeps previously downloaded files so it can skip them on future runs, and `calibredb add` ignores duplicates.

```bash
# Download all books from Kobo
docker compose exec -T kobodl kobodl book get --get-all --output-dir /downloads

# Import any new EPUBs into Calibre library
docker compose exec -T --user abc calibre-web sh -c '
  for f in /downloads/*.epub; do
    [ -f "$f" ] || continue
    calibredb add "$f" --with-library /library/ || true
  done
'
```

This runs on demand via `make calibre-sync`. The whole library is available at `books.monotrope.au`, behind Caddy's automatic TLS.

## The reader: KOReader

This is where it gets interesting. [KOReader](https://koreader.rocks/) is an open-source document reader that can replace the stock Kobo firmware. It runs on the device itself — you install it alongside the stock software and can switch between them.

KOReader is relevant here because it tracks reading statistics locally in a SQLite database on the device. Pages read, time spent, reading sessions — all stored in structured data that you own. The stock Kobo reader tracks some of this too, but you can't get at the data.

KOReader also has a plugin ecosystem, which is what connects it to the rest of the stack.

## Reading stats: KoInsight

[KoInsight](https://github.com/GeorgeSG/KoInsight) is a web dashboard for KOReader reading statistics. It comes in two parts: a server component that stores and displays the data, and a KOReader plugin that syncs stats from the device over wifi.

The server is another Docker container on my VPS, exposed through Caddy at `koinsight.monotrope.au`. The KOReader plugin runs on the Kobo and pushes reading session data to the server whenever the device is on wifi.

This is the part that actually answers the original question: detailed reading stats, self-hosted, based on data I own. Time per book, pages per day, reading streaks — all derived from real reading sessions tracked on the device.

## How it all fits together

The data flow looks like this:

1. **Buy a book** on the Kobo store (or side-load an EPUB)
2. **kobodl** downloads and de-DRMs purchased books
3. **calibre-web** catalogues the library, provides a web UI for browsing and downloading
4. **KOReader** on the Kobo reads the books and tracks reading statistics locally
5. **KoInsight** receives stats from KOReader over wifi and displays them in a web dashboard

Each piece is a separate Docker container (or in KOReader's case, firmware on the device), managed through Ansible and proxied through Caddy. The whole thing is configured in about 100 lines of Ansible and a couple of small Docker Compose files.

## Was this worth it?

For the reading stats alone? Probably not. I could have just looked at my Kobo's "reading life" screen and called it a day.

But the stats were the wedge. What I actually ended up with is a system where I fully own my reading data — the books themselves, the library metadata, and the reading history. None of it depends on Kobo's servers staying up, or Rakuten not getting acquired, or some product manager deciding to deprecate an API.

The whole setup took a few hours across a couple of evenings, almost entirely through Claude Code writing the Ansible playbooks and Docker configs. That's the thing about self-hosting in 2026 — the operational complexity that used to make this impractical has been dramatically reduced. Not eliminated, but reduced enough that the trade-off has shifted for a lot more people.

If you read on a Kobo and care about owning your data, I'd recommend this stack. KOReader alone is worth the install even without the rest of it.
