---
title: "AI feels both alienating and anti-alienating"
date: 2026-04-14
draft: true
tags:
- ai
- capitalism
---

Not even 12 months ago, if you had a meeting at work and someone took an action to write up a plan for the project, you had probably a week or two of breathing room before you heard about it again. They'd go away, write a shitty draft that was barely more than a couple of bullet points, have a 1:1 with the PM in another team to get their feedback, flesh it out, iterate, workshop it with their team, and then maybe you have something that looks like a plan. The document reflects the alignment. Everyone has more or less the same picture in their heads.

Now, you finish the meeting and 37 seconds later there's a fully fleshed out project plan on Confluence (or worse there are 3 different ones published by 3 different people) but none of the alignment has happened, and there isn't even a complete mental model of the plan in a single person's head. It's not "workslop" strictly, because it's not gibberish. It can be a mostly coherent project plan, that if everyone actually followed would have a decent chance of working. But we're so used to "document exists, therefore alignment exists" as a heuristic that it takes weeks/months to even realise that no one truly understands the plan on a cellular level.

This is fucking exhausting.

But the thing that is not fucking exhausting is building cool websites and apps with Claude Code in the evengings. _Years_ of half-baked backlog ideas of _maybe when I have more time_ stuff that you can just materialise by talking to your terminal.

I was annoyed that I couldn't get good reading stats from my Kobo. So I spent a few hours going down a rabbit-hole, replacing the firmware with KOReader, standing up Calibre-Web on my VPS, and building an automated ingestion pipeline where I forward my purchase receipt email to an AI agent that automatically signs in, downloads the book, removes the DRM, and adds it to my Calibre library, all so I can auto-sync reading stats to an sqlite database and visualise my reading time. This whole thing took maybe 3 hours, which is _insane_.

In any year prior to 2026 this thing would have died at the first hurdle because I hit some weird error in docker-compose and it was 9pm and I was too tired to look up the syntax, and that would have been before literally any part of the thing had shipped.

I have an unprecedented amount of power to build whatever I want whenever I feel like it, and (at least for the moment) this costs me less than my Netflix subscription.

I live a double life, where AI is both draining and replenishing my life energy in alternating waves.

## Enter, Marx

This all boils down to Marx's idea of _alienation_. When I stand up my own webserver to deliver books _sans_ DRM to my eReader, and then sync my stats back as an sqlite file, I am owning the product of my work, engaging fully with the design and creative process, and doing something that matters to me. When someone writes a product plan without thinking it through or talking to anyone, they are _increasing_ their alienation from both the process and craft of their work as well as from other people.

Jasmine Sun wrote this in [claude code psychosis](https://jasmi.news/p/claude-code) and I love it:

> Moreover, if you’re sick of the corporate web or miss aesthetic variety, the home-cooked app renaissance is as good as it gets. I made sites to track meals, my iMessage stats, and every time a nation declared a “Sputnik moment.” Goodbye to the airspace era of software design—I’m delighted to have more opinionated software, where scalemaxxed sterility is replaced with bespoke builds and pizzazz. And as with the digital democratization of publishing, photography, and more, I believe creativity will emerge from everywhere. The number of fun websites, games, and apps will explode.

This is the opposite of alienation.

Marx was writing about the industrial revolution, and the alienation was driven in part by the inaccessibility of the machines and capital to the workers. Weavers could not set up indie shops running steam looms because the investment required for a factory was too large. But since the early days of the web software has been democratising, and AI can be the same. We've gradually shifted away from the indie web as the convenience and capability of centralised platforms grew, but in a lot of ways AI coding might be able to reverese that trend.

The open question in my mind is the fourth kind of alienation. Working with AI tools is in many ways more solitary than the tech work of the last few decades. I'm curious to see if we can overcome this and learn to fight back against this form of alienation as well, or whether this will be a k-shaped recovery, where AI is anti-alienating in the product/process axes but _increases_ alienation in the essence/others axes.
