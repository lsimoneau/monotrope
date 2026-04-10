---
title: "An Experiment in Self-Hosting"
date: 2026-04-10T00:00:00+10:00
draft: false
---

One of the things I wanted to do with this site is to see how much tooling I could self-host on a small VPS, in particular with the acceleration afforded by AI coding through Claude Code.

So far I have:

* A [Hugo](https://gohugo.io/) static site
* [Caddy](https://caddyserver.com/) webserver
* Self-hosted feed reader with [Miniflux](https://miniflux.app/)
* Analytics using [Goatcounter](https://www.goatcounter.com/)
* Git server using [Gitea](https://about.gitea.com/) (you can check out the source for the whole project, inception-style, at [git.monotrope.au/louis/monotrope](https://git.monotrope.au/louis/monotrope))

The only external dependency for the whole setup is the server itself (a DigitalOcean droplet), and I'm sure I'll come up with more tools I can add to the server over time.

All of this I would estimate took less than 4 hours to set up and deploy. I think previously even the small amount of effort required to deploy a static blog would have pushed me towards free platforms like Medium or GitHub Pages. This mode of production has the potential be a great thing for the Web if more tinkerers can build and host their own stuff instead of relying on centralised platforms where you are the product.