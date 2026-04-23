# Ambient Agents Plan

A personal plan for building a small portfolio of scheduled hermes-agent
workflows that do synthesis work against my Obsidian vault and calendar
without me having to remember to trigger them.

## Goal

The problem this solves is adoption, not capability. My `/daily-plan` skill
in Claude Code produces good output, but I don't always run it. On mornings
with an early meeting the tool never opens and the day runs me instead.

The project is to take the synthesis work I do well interactively and move
the high-leverage pieces to scheduled jobs on my VPS, so they run whether or
not I remember. The outputs land in my vault as regular notes. When I open
Obsidian in the morning, the plan is already there.

## Secondary goals

- Build real operational intuition for running agents in production:
  observability, failure handling, secrets, scheduling, context design.
  This transfers directly to agent deployments at work.
- Develop craft for skills that run unattended, which is a more demanding
  design problem than skills used interactively.
- Possibly release a skills package or playbook at the three-month mark, if
  what I've built generalises enough to be useful to others.

Not a goal: general agentic coding practice on large codebases. That's a
legitimate gap but this project doesn't serve it well. Revisit at the
three-month checkpoint whether to add a second track for that.

## Status

Pre-Week-1 state management work is done (see "Week 0" below). Next up is
Week 1: headless Obsidian + Sync on the VPS. Safe to clear context and
resume from there.

## Architecture decisions

Made:

- Hermes on the Sydney VPS, reached from laptop and phone via the messaging
  gateway and HTTP API.
- Hermes stays in its own container. Obsidian will run alongside it, not
  inside the same container. Hermes reaches the vault via direct filesystem
  read/grep on the shared markdown tree rather than MCP (context bloat, worse
  performance) or the Obsidian CLI (needs Electron).
- Headless Obsidian plus Obsidian Sync running on the VPS against the
  existing vault. Hermes writes plain markdown; Obsidian handles sync and
  any template/link fixups as a side-effect of the vault being live.
- Calendar access via iCal subscribe: share CA gcal to my personal Google,
  generate private iCal URL, point hermes at it. No OAuth, read-only.
- Output convention: every skill writes a summary note to `agent-reports/`
  regardless of what else it does. The vault is the log.
- No plugin in v1. The vault is the surface.
- Hermes skills are seeded into a named volume on deploy (no bind-mount).
  Repo holds seeds; server copy evolves freely without ansible clobbering
  it. See `infra/hermes/seeds/`.
- Hermes state is backed up two ways: nightly `hermes backup --quick`
  snapshots (14-day retention on disk) and a 30-min git push of the
  diff-able volume contents (skills/, cron/, SOUL.md, config.yaml) to a
  private `louis/hermes-state` repo in gitea. Memory lives in state.db and
  is only covered by the nightly snapshot.

Deferred:

- TypeScript Obsidian plugin. Reconsider when specific output-surface
  problems emerge that markdown notes can't solve.
- Google Calendar OAuth. Only if iCal read-only becomes limiting.
- Cross-note dashboards or Dataview-driven views. Tried before, didn't
  stick. Individual fresh notes beat continuously-queried views.
- Open source release decision. Decide at three-month checkpoint.

Out of scope permanently:

- Direct Culture Amp GWS API access from the VPS.
- Mobile UX work.
- Multi-user or team-shared version.
- Chat interface in Obsidian. Terminal and Signal already cover that.

## Week 0: State management (done)

Done before touching Obsidian, because the existing hermes install had no
backups and a bind-mount for skills that would lose server-side evolution
on every deploy. What shipped:

- Skills moved from bind-mount to a named volume, with a seed-at-deploy
  pattern (`infra/hermes/seeds/` → `hermes_data` volume, no-clobber copy).
  Ansible no longer overwrites agent-authored skill drift.
- Nightly `hermes backup --quick` at 18:00 UTC via systemd timer,
  14-day on-disk retention. Snapshots include state.db (memory + cron
  history), config, auth, .env, cron definitions.
- Git sidecar pushing the diff-able volume contents (skills/, cron/,
  SOUL.md, config.yaml) to a private `louis/hermes-state` repo in gitea
  every 30 min. No-op when nothing changed. Gitea joined the `monotrope`
  docker network so the push is container-to-container.
- Gitea given `container_name: gitea` so it's reachable on the bridge
  network by name.

Not done, deliberately deferred:

- Offsite copy of nightly snapshots (restic/borg → B2). Single-region
  failure is the main uncovered risk; add if/when it matters.
- Syncing server-side skill evolution back into the repo seeds. Current
  seeds are a good enough baseline.

## Weeks 1-4: Build sprint

Target: two skills running reliably on schedule, writing useful notes to the
vault, with basic observability.

### Week 1: Infrastructure

- Set up headless Obsidian on the VPS. Verify it stays running.
- Configure Obsidian Sync to run on the server against my existing vault.
- Register and test the official Obsidian CLI. Verify: commands run on the
  VPS produce changes that sync back to my laptop.
- Document the setup in a README inside this directory so I can rebuild it.

Open questions to resolve this week:

- Does headless Obsidian actually run stably on Ubuntu? How is it supervised
  (systemd unit, Docker, something else)?
- How are credentials managed for Obsidian Sync on the server?

### Week 2: Hermes foundation plus daily-plan skill

- Confirm hermes install is current, has API server enabled, auth configured.
- Figure out hermes' cron API and skill format in enough detail to write
  and verify a skill.
- Share CA gcal to personal Google account, generate iCal URL, configure
  hermes with iCal access.
- Port `/daily-plan` from Claude Code to a hermes skill. Run it manually
  via hermes CLI. Iterate on the prompt until the output looks right.

Success criteria: I can run `daily-plan` via hermes and get output at least
as good as the Claude Code version.

### Week 3: First scheduled skill

- Configure hermes cron to run daily-plan at 6:30am weekdays.
- Output convention: writes to `agent-reports/daily/YYYY-MM-DD.md`.
- Add failure notification to Signal or Telegram when the cron job fails.
- Live with it for at least one work week. Read the output every morning.
  Note what's good and what's bad, but don't fix anything yet.

Success criteria: reliable Monday-to-Friday execution. Plan is on my vault
when I sit down.

### Week 4: Second skill plus observability

- Port weekly delegated items review. Schedule it for Friday 4pm. Output
  to `agent-reports/weekly/delegated-items-YYYY-MM-DD.md`.
- Add basic agent activity log. Could be a weekly summary note the agent
  writes itself, or a small CLI tool I can run locally.
- First retrospective on the daily-plan skill: what would I change?
  Change one thing. Not three.

Success criteria: two skills running, I know what failure looks like and
how I'd notice it, I've made one deliberate iteration based on real use.

## Weeks 5-12: Live with it

This is the high-learning phase and it requires elapsed time, not many
hours. Keep building to a minimum. Focus on noticing.

Weekly habit, Friday afternoon, fifteen minutes:

- What did the agent do well this week?
- What did it do badly?
- What one thing would I change?
- Track answers in `agent-reports/reviews/YYYY-MM-DD.md`.

Things to watch for, roughly in order of interest:

- Am I actually reading the daily plan? Is it changing my day? If not,
  why not, and is it a skill problem or an adoption problem?
- What's fragile? Public holidays, travel weeks, weeks where my vault is
  unusually messy, credential expiry, hermes or Obsidian updates.
- What skills do I wish existed? Note them in a wishlist. Don't build
  anything new until week 12.

Explicit non-goal for this phase: adding new skills. The temptation will
be real. Resist.

Success criteria at week 12:

- Daily plan and weekly review running reliably for eight consecutive
  weeks.
- I use the daily plan most mornings.
- Wishlist of three to five new skill ideas, prioritised.
- I can describe the operational patterns clearly enough to explain them
  to someone at work.

## Weeks 13-26: Deliberate expansion

Decisions to make at the start of this phase:

- Which two or three skills from the wishlist to port next?
- Is the plugin worth building now, or is vault-as-dashboard still
  sufficient?
- Is there enough here to release as an open source skills package? If
  yes, what would it contain?
- Add a second learning track for agentic coding on real codebases, or
  defer?

Candidates from the wishlist (to be re-evaluated at month 3):

- Sunday evening week-ahead briefing.
- Writing practice nudges: surface idle drafts, suggest what to pick up.
- Monthly skip-level summary across the four teams.
- 1:1 prep generator, triggered the morning of each 1:1.
- Reading inbox processing: things I've saved, synthesised into a
  weekly digest.

The shape of this phase is: add one skill, live with it for two to three
weeks, add the next. Same discipline as weeks 1-12. Don't stack.

## Repo structure

Proposed layout for this directory in the monotrope repo:

```
hermes/
  PLAN.md                 # this file
  README.md               # setup instructions, how to rebuild
  skills/                 # hermes skill source (markdown)
    daily-plan/
    delegated-items-review/
  config/                 # hermes config, cron definitions
  infrastructure/         # systemd units, Docker, whatever ends up here
```

Skills might end up somewhere else depending on how hermes expects them
laid out. Adjust as needed.

## Review cadence

- Weekly Friday review during the live-with-it phase (weeks 5-12).
- Three-month checkpoint at end of week 12: full retrospective, decide
  expansion phase shape.
- Six-month checkpoint at end of week 26: decide what's next. Possibly
  this project ends here and something else begins.
