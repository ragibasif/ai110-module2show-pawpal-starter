# PawPal+ Project Configuration

## gstack

Use the `/browse` skill from gstack for all web browsing. Never use `mcp__claude-in-chrome__*` tools.

To install gstack:
```bash
git clone --single-branch --depth 1 https://github.com/garrytan/gstack.git ~/.claude/skills/gstack && cd ~/.claude/skills/gstack && ./setup
```

Available gstack skills:
- `/office-hours` — office hours workflow
- `/plan-ceo-review` — CEO review planning
- `/plan-eng-review` — engineering review planning
- `/plan-design-review` — design review planning
- `/design-consultation` — design consultation
- `/design-shotgun` — design shotgun workflow
- `/review` — code review
- `/ship` — full ship workflow
- `/land-and-deploy` — land and deploy
- `/canary` — canary deployment
- `/benchmark` — benchmarking
- `/browse` — web browsing (use this for all web browsing)
- `/connect-chrome` — connect to Chrome
- `/qa` — QA workflow
- `/qa-only` — QA only workflow
- `/design-review` — design review
- `/setup-browser-cookies` — set up browser cookies
- `/setup-deploy` — set up deployment
- `/retro` — retrospective
- `/investigate` — investigation workflow
- `/document-release` — document a release
- `/codex` — Codex workflow
- `/cso` — CSO workflow
- `/autoplan` — automated planning
- `/careful` — careful mode
- `/freeze` — freeze changes
- `/guard` — guard mode
- `/unfreeze` — unfreeze changes
- `/gstack-upgrade` — upgrade gstack to latest
