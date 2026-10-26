# Vetted tools (starter list)

Checked on 2026-10-24: alive (pushed within the last two weeks), licensed, real code or real
skills, no affiliate funnel. Pin after approval. Stars are from the
GitHub API on that date and are not the reason for the pick. Re-check before pinning.

| Need | Tool | License | Notes |
|---|---|---|---|
| Local business leads (maps) | github.com/gosom/google-maps-scraper | MIT | Go CLI/REST/web UI; ~6.8k stars; README has sponsor banners only |
| Social post scheduling | github.com/gitroomhq/postiz-app | AGPL-3.0 | Self-hosted, API hooks; ~37.7k stars; fine to run, not to embed in closed source |
| Social writing skills | github.com/charlie947/social-media-skills | MIT | 17 Agent Skills (post writer, hooks, reels); optional Apify/Gemini keys; ~4.3k stars |
| Agent personas | github.com/wshobson/agents · github.com/msitarzewski/agency-agents | MIT | Hundreds of persona files; pin single personas, never the whole repo |
| Topic → short video | github.com/harry0703/MoneyPrinterTurbo | MIT | Real app; README full of affiliate links, code runs with your own keys; ~134k stars |
| Long video → shorts | github.com/Anil-matcha/AI-Youtube-Shorts-Generator | MIT | ~5.6k stars |
| WhatsApp automation | github.com/wwebjs/whatsapp-web.js · github.com/WhiskeySockets/Baileys | Apache-2.0 · MIT | Unofficial clients; check WhatsApp's terms for the use case |

## Cost and usage (checked 2026-10-26)

| Need | Tool | License | Notes |
|---|---|---|---|
| Budget guard + where the money went | github.com/getagentseal/codeburn | MIT | Local only; `codeburn guard install` adds Claude Code hooks that warn at $5 and stop at $15 per session; `codeburn audit` explains every number; ~11.6k stars |
| Cache-hit and spend meter | github.com/ccusage/ccusage | MIT | Reads the local session files; separates cache reads/writes; `ccusage statusline`; covers Claude Code, Codex, OpenCode, Gemini CLI; ~19k stars; monorepo, so GitHub's API shows no license, the app's own LICENSE file is MIT |
| Shorter shell output in context | github.com/rtk-ai/rtk | Apache-2.0 (+BUSL engine; `rtk-oss` is pure Apache) | Rewrites Bash output before it reaches the model; independent measurement (Quesma, Terminal-Bench 2.1, 1,740 runs): about 5% lower bill, pass rate 84→83%. Useful when logs are verbose, not a big saver |

Cost claims without a method behind them are not evidence: "30–50%", "50%+" and "10x" appear in
popular READMEs with no measurement. Point users at `docs/cost.md` for how to measure instead.

## Avoid

- `cporter202/*` "APIs and scrapers" repos: catalogs of affiliate links (same tracking code on
  every link), two without a license, no code.
- `RayVentura/ShortGPT`: last push 2025-02.
- `contains-studio/agents`: no license, last push 2025-07.
- Routing proxies that take your API key or relay traffic through third parties
  (`musistudio/claude-code-router`, `farion1231/cc-switch`'s sponsored relays): savings come
  from reselling, and a gateway that drops `cache_control` makes every turn full price.
- `thedotmack/claude-mem`: memory leaves the machine to a hosted service by default.

## Rejected for a reason worth remembering

A high star count was not enough on its own; two of the avoided repos have more stars than
some of the picks. Evidence that it works, a license, and no funnel decide.
