---
title: "AIlienation"
date: 2026-04-14
draft: false
tags:
- ai
---

Last week I was annoyed that I couldn't get good reading stats from my Kobo. So I spent a few hours going down a rabbit-hole, replacing the firmware with [KOReader](https://koreader.rocks/), standing up [Calibre-Web](https://github.com/janeczku/calibre-web) on my VPS, and building an automated ingestion pipeline where I forward my purchase receipt email to an AI agent that automatically signs in, downloads the book, removes the DRM, and adds it to my Calibre library, all so I can auto-sync reading stats to an sqlite database and visualise my reading time. This whole thing took maybe 3 hours, which is _insane_.

In any year prior to 2026 this idea would have died at the first hurdle because I hit some weird error in docker-compose and it was 9pm and I was too tired to look up the syntax, and that would have been before literally any part of the thing had shipped.

I have an unprecedented amount of power to build whatever I want whenever I feel like it, and (at least for the moment) this costs me less than my Netflix subscription. But at the same time, the kind of work I do for money feels measurably worse.

Not even 12 months ago, if you had a meeting at work and someone took an action to write up a plan for a project, you had probably a week or two of breathing room before you heard about it again. They'd go away, write a shitty draft that was barely more than a couple of bullet points, have a 1:1 with a PM in another team to get their feedback, flesh it out, iterate, workshop it with their team, and then maybe you have something that looks like a plan. The document reflects the alignment. Everyone has more or less the same picture in their heads.

These days, you finish the meeting and 37 seconds later BAM! there's a fully fleshed out project plan on Confluence (or worse, there are 3 different ones published by 3 different people) but none of the alignment has happened, and there isn't even a complete mental model of the plan in a single person's head. It's not "workslop" exactly, because it's not gibberish. It's a mostly coherent plan, that if everyone actually followed would have a decent chance of working. But we're so used to "document exists, therefore alignment exists" as a heuristic that it takes weeks/months to even realise that no one truly understands the plan on a cellular level.

This is fucking exhausting.

I increasingly feel like I live in two worlds, AI both draining and replenishing my life energy in alternating waves.

## Enter, Marx

AI turbo-charges [alienation](https://en.wikipedia.org/wiki/Marx%27s_theory_of_alienation) at work: collaboration atrophies as we all retreat to our chatbot silos, and we're disconnected from both process and outcome. But hacking on a side project, the gap between idea and execution is narrowed down to the subatomic scale. Ideas are made manifest on a whim; the dark alleyways of side quests beckon alluringly when you know they're quicker than a coffee run. The AI agent on my server is inessential, I could have put a full re-sync on a cron job, but fuck it we've got the tokens.

Jasmine Sun wrote this in [claude code psychosis](https://jasmi.news/p/claude-code) and it captures the vibe:

> Moreover, if you’re sick of the corporate web or miss aesthetic variety, the home-cooked app renaissance is as good as it gets. I made sites to track meals, my iMessage stats, and every time a nation declared a “Sputnik moment.” Goodbye to the airspace era of software design—I’m delighted to have more opinionated software, where scalemaxxed sterility is replaced with bespoke builds and pizzazz. And as with the digital democratization of publishing, photography, and more, I believe creativity will emerge from everywhere. The number of fun websites, games, and apps will explode.

This is the opposite of alienation.

Marx was writing about the industrial revolution, and the alienation was driven in part by the inaccessibility of the machines and capital to the workers. Weavers could not set up indie shops running steam looms; the investment required for a factory was too large. But since the early days of the web, software has been democratising; AI has the same potential. We've gradually shifted away from the indie web as the convenience and capability of centralised platforms grew, but that trend is reversing.

But are we still alienating ourselves from other people? We adopted pair (and even mob) programming and reaped the benefits of shared understanding _and_ human connection, but now the LLM often takes the role of the pair. Hacking on a side project at the speed of thought does nothing to address that species of alienation. How will workplaces and communities (like open-source projects or federated networks) adapt to collaboration when non-human entities are part of the mix? AI girlfriends and therapists manifest this alienation in the intimate sphere, but the bigger arena of collectives and organisations hasn't been reshaped to anywhere near the same extent.