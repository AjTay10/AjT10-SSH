---
name: reach-social
description: >
  Read the major social platforms and any website with zero API keys.
  Use this INSTEAD of the built-in web/x_search toolsets whenever you need
  X/Twitter, Reddit, Instagram, TikTok, Facebook, LinkedIn, Threads, Bluesky,
  Mastodon, Telegram, Pinterest, YouTube, Wikipedia, Hacker News, Stack
  Overflow, Snapchat, Discord, Twitch, Tumblr, VK, Vimeo, Weibo, Quora, Douyin,
  Xiaohongshu/RED, Bilibili, Medium or Substack — and for reading or searching
  any ordinary web page or RSS feed.
  The built-in web toolset needs EXA_API_KEY / TAVILY_API_KEY /
  FIRECRAWL_API_KEY and x_search needs XAI_API_KEY; none are configured here,
  so those tools will fail. `reach` needs none of them.
  Read-only: it never posts, comments or likes.
platforms: [linux, macos]
---

# reach — social platforms and web, no API keys

`reach` is on PATH. Every command prints readable text, accepts `--json` for
structured output, `-n N` to cap results, and `--max-chars N` to cap page text.

Check availability first if unsure: `reach doctor` probes all 31 platforms live
in about a minute and prints which backend currently serves each one.

## Routing table

| Need | Command |
|------|---------|
| read any web page or article | `reach web URL` |
| search the open web | `reach search "QUERY"` |
| a post on X/Twitter | `reach x URL_OR_ID` |
| what X is saying about a topic | `reach x "QUERY"` |
| Reddit threads | `reach reddit "QUERY"` or `reach reddit URL` |
| Bluesky | `reach bluesky "QUERY"`, or `reach bluesky x --user HANDLE` |
| Mastodon | `reach mastodon TAG` or `reach mastodon STATUS_URL` |
| public Telegram channel | `reach telegram CHANNEL` |
| TikTok | `reach tiktok URL_OR_QUERY` |
| Instagram | `reach instagram URL_OR_QUERY` |
| Facebook | `reach facebook URL_OR_QUERY` |
| LinkedIn profile/company | `reach linkedin URL_OR_QUERY` |
| Threads | `reach threads URL_OR_QUERY` |
| Pinterest | `reach pinterest URL_OR_QUERY` |
| YouTube video or search | `reach youtube URL_OR_QUERY` |
| Wikipedia | `reach wikipedia "QUERY" --full` |
| Hacker News | `reach hn "QUERY"` |
| Stack Overflow | `reach stackoverflow "QUERY"` |
| Snapchat public profile | `reach snapchat USER_OR_URL` |
| Discord server (invite/widget) | `reach discord INVITE_OR_GUILD_ID` |
| Twitch channel, video or clip | `reach twitch CHANNEL_OR_URL` |
| Tumblr blog | `reach tumblr BLOG_OR_URL` |
| VK profile, group or post | `reach vk USER_OR_URL` |
| Vimeo video | `reach vimeo URL_OR_QUERY` |
| Weibo posts | `reach weibo "QUERY"` |
| Quora questions and answers | `reach quora URL_OR_QUERY` |
| Douyin video | `reach douyin URL_OR_QUERY` |
| Xiaohongshu / RED post | `reach xiaohongshu URL_OR_QUERY` |
| Bilibili video | `reach bilibili URL_OR_QUERY` |
| Medium profile or publication | `reach medium URL_OR_QUERY` |
| Substack newsletter | `reach substack URL_OR_QUERY` |
| any RSS/Atom feed, or a site's feed | `reach rss URL` |

Anything with a URL takes the URL; anything else takes a search phrase. Phrase
searches as a description of the ideal page, not as keywords.

## Rules

1. Exit codes: `0` ok, `3` empty, `4` needs credentials, `5` every backend
   failed. On 4 or 5, report what is blocked — never silently substitute.
2. Some platforms only yield metadata or a search index because they gate post
   detail behind a login: TikTok, Instagram, Facebook, LinkedIn, Threads,
   Pinterest, Reddit, VK, Weibo, Quora, Douyin, Xiaohongshu. `reach` prints a `[note: ...]` banner when it is handing
   back a substitute; **repeat that caveat** rather than presenting it as the
   platform's own content.
3. Full content is available for: web pages, search, X posts, Bluesky,
   Mastodon, Telegram, YouTube, Wikipedia, Hacker News, Stack Overflow,
   RSS/Atom feeds, Medium, Substack, Tumblr, Vimeo, Discord server metadata.
4. Read-only. To *send* a message, use the Hermes messaging tools
   (`hermes send`, or the gateway) — not this skill.
5. Write scratch output to `/tmp`, never into a workspace or repo.

## Examples

```bash
reach search "independent benchmarks comparing vector databases 2026" -n 5
reach x https://x.com/user/status/1234567890123456789
reach reddit "experiences self-hosting immich" --subreddit selfhosted
reach bluesky "anthropic" -n 10
reach telegram durov -n 5
reach web https://example.com/post --max-chars 4000
reach youtube "https://www.youtube.com/watch?v=VIDEOID" --json
reach discord https://discord.gg/INVITE
reach rss https://blog.rust-lang.org        # autodiscovers the feed
reach substack https://bigtechnology.substack.com -n 5
```

## When reach is unavailable

If `reach` is not on PATH, it is installed by
`scripts/install-agent-reach.sh` in the AjT10-SSH repo. Fall back to the
built-in `web` toolset only if its API keys are configured — otherwise say the
capability is missing instead of guessing at content.
