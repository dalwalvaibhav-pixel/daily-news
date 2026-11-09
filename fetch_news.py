"""Vaibhav's Daily Newspaper
Gemini free API + Google Search grounding -> detailed sections -> static HTML (GitHub Pages).
Edit the SECTIONS list below to add, remove or change any section or prompt.
"""
import os, re, sys, time, html, datetime, pathlib
import requests, markdown

IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")   # change if Google renames it
API_KEY = os.getenv("GEMINI_API_KEY", "")
PAUSE = int(os.getenv("PAUSE_SECONDS", "12"))           # pause between calls (free-tier rate limit)

SYSTEM = (
    "You are the chief editor of a detailed daily newspaper for a senior B2B sales and account "
    "management professional in Mumbai, India, working in HR-tech. Use Google Search to find real, "
    "current news. Never invent facts, numbers or links. Write in your own words (do not copy "
    "article text). Be detailed and specific."
)

RULES = """For EVERY story use this format:
### Headline
**Date:** published date | **Source:** source name (with link)
What happened, key numbers, and context, in as much detail as needed. No length limit.
Never write "no update" without giving the most recent available item with its date.
Do not add any introduction or closing remarks; start directly with the first story."""

WHY = "\nEnd the section with a short **Why this matters for my B2B sales and account management career** note."


def P(window, body, why=False):
    return f"Time window: {window}.\n{body}\n\n{RULES}" + (WHY if why else "")


def india_batch(lo, hi):
    return P("last 7 days",
             f"Companies: the current official Nifty 100 index constituents, ranked {lo}-{hi} by market cap. "
             "For each company that has news in the window, cover it fully (results, deals, leadership, "
             "expansion, hiring, regulatory, stock moves). Skip companies with no news. "
             "At the end add one line: 'No news found for: ...' listing skipped companies.")


def world_batch(lo, hi):
    return P("last 7 days",
             f"Companies: the 100 largest companies in the world by market cap (use a current list such as "
             f"companiesmarketcap.com), ranked {lo}-{hi}. For each company that has news in the window, "
             "cover it fully. Skip companies with no news. "
             "At the end add one line: 'No news found for: ...' listing skipped companies.")


SECTIONS = [
    {"id": "hrtech", "title": "HR-Tech & Recruitment", "prompts": [P(
        "last 7 days",
        "Cover 10 stories on HR-tech and recruitment, big or small companies. Check People Matters, "
        "ETHRWorld, Economic Times HR, Naukri, LinkedIn News and other recruitment platforms.", why=True)]},
    {"id": "jobs", "title": "India Job Market & Hiring", "prompts": [P(
        "last 7 days",
        "Cover 10 stories on the India job market and hiring, each with numbers (hiring data, salary "
        "trends, layoffs, GCC expansion, sector demand).", why=True)]},
    {"id": "targets", "title": "Target Companies: Salesforce India, Darwinbox, Freshworks, Microsoft India",
     "prompts": [P(
         "latest available (even if older; show the date)",
         "Give the latest news on EACH of these four companies under its own heading: Salesforce India, "
         "Darwinbox, Freshworks, Microsoft India. Include leadership changes, products, expansion, "
         "hiring and open roles in India, and anything relevant to selling to or joining them.", why=True)]},
    {"id": "b2b", "title": "B2B Sales, SaaS & AI-in-Sales", "prompts": [P(
        "last 7 days",
        "Cover 10 stories on B2B sales, SaaS and AI in sales (tools, funding, strategy, enterprise "
        "buying trends).", why=True)]},
    {"id": "markets", "title": "Markets & Economy", "prompts": [P(
        "last 24 hours",
        "Cover Sensex, Nifty, the rupee, RBI, FII/DII flows, crude and global cues. For each, give the "
        "closing numbers and the reasons behind the move. Add a short 'what to watch tomorrow' list.")]},
    {"id": "it", "title": "IT Product & IT Services Companies", "prompts": [P(
        "last 7 days",
        "Cover every notable story on IT services (TCS, Infosys, Wipro, HCL, Tech Mahindra, LTIMindtree "
        "and others) and IT product companies and big tech: deals, results, layoffs, hiring, AI.")]},
    {"id": "finance", "title": "Financial Services: Banks, NBFCs, Insurance, Fintech", "prompts": [P(
        "last 7 days",
        "Cover every notable story on banks, NBFCs, insurers, fintechs, mutual funds and RBI/SEBI "
        "actions: what is coming in (new launches, approvals, funding, appointments) and going out "
        "(exits, penalties, closures, layoffs).")]},
    {"id": "startups", "title": "Startup Funding & IPOs", "prompts": [P(
        "last 7 days",
        "Cover every notable startup funding round and IPO (open, upcoming, listed) with amounts, "
        "investors, valuation and price bands where available.")]},
    {"id": "india-cos", "title": "Top 100 Indian Companies",
     "prompts": [india_batch(1, 25), india_batch(26, 50), india_batch(51, 75), india_batch(76, 100)]},
    {"id": "world-cos", "title": "Top 100 Global Companies",
     "prompts": [world_batch(1, 25), world_batch(26, 50), world_batch(51, 75), world_batch(76, 100)]},
    {"id": "mumbai", "title": "Mumbai", "prompts": [P(
        "last 24 hours",
        "Cover 10 Mumbai stories: civic, transport (local trains, metro, roads), business, real estate, "
        "weather and safety.")]},
    {"id": "world", "title": "World", "prompts": [P(
        "last 24 hours",
        "Cover 20 world stories grouped by region (US, Europe, Middle East, Asia, Africa, Americas). "
        "Add the India angle where relevant.")]},
    {"id": "skill", "title": "Skill of the Day", "prompts": [
        "Give ONE practical skill idea for a senior B2B sales and account management professional in "
        "HR-tech who wants to grow into roles at companies like Salesforce, Darwinbox, Freshworks or "
        "Microsoft. Include why it matters, and a 15-minute practice task. Use Markdown. No introduction."]},
]


def gemini(prompt, date_str):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
    body = {
        "systemInstruction": {"parts": [{"text": SYSTEM + f" Today's date is {date_str} (IST)."}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 20000},
    }
    for attempt in range(5):
        try:
            r = requests.post(url, json=body, headers={"x-goog-api-key": API_KEY}, timeout=300)
        except requests.RequestException as ex:
            print("Network error:", ex)
            time.sleep(20)
            continue
        if r.status_code == 200:
            cand = (r.json().get("candidates") or [{}])[0]
            parts = cand.get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts).strip()
            sources, seen = [], set()
            for c in cand.get("groundingMetadata", {}).get("groundingChunks", []):
                w = c.get("web", {})
                u = w.get("uri")
                if u and u not in seen:
                    seen.add(u)
                    sources.append((w.get("title") or u, u))
            if text:
                return text, sources
            print("Empty response, retrying")
        elif r.status_code in (429, 500, 503):
            wait = 30 * (attempt + 1)
            print(f"Gemini {r.status_code}, waiting {wait}s")
            time.sleep(wait)
            continue
        else:
            print(f"Gemini error {r.status_code}: {r.text[:300]}")
            break
    return None, []


def md_to_html(text):
    text = re.sub(r"(?is)<script.*?</script>", "", text)
    out = markdown.markdown(text, extensions=["extra", "sane_lists"])
    return out.replace("<a href=", '<a target="_blank" rel="noopener" href=')


CSS = """
:root{--bg:#faf8f3;--fg:#1a1a1a;--mut:#666;--line:#d8d2c4;--acc:#8b1a1a;--card:#fff}
@media(prefers-color-scheme:dark){:root{--bg:#161616;--fg:#eee;--mut:#9a9a9a;--line:#333;--acc:#e08a8a;--card:#1e1e1e}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font-family:Georgia,'Times New Roman',serif;line-height:1.6}
.wrap{max-width:900px;margin:0 auto;padding:20px 16px}
header{text-align:center;border-bottom:3px double var(--fg);padding-bottom:12px;margin-bottom:16px}
h1{font-size:clamp(26px,6vw,46px);margin:0;letter-spacing:1px}
.date{color:var(--mut);font-size:14px;margin-top:4px}
nav{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 24px;padding:0}
nav a{font:13px system-ui,sans-serif;border:1px solid var(--line);border-radius:999px;padding:5px 12px;color:var(--fg);text-decoration:none;background:var(--card)}
section{margin-bottom:40px}
section>h2{border-bottom:2px solid var(--acc);padding-bottom:4px;color:var(--acc);text-transform:uppercase;font-size:17px;letter-spacing:2px}
section h3{font-size:19px;margin:22px 0 4px}
section p{margin:4px 0 10px}
a{color:var(--acc)}
details{font:13px system-ui,sans-serif;color:var(--mut);margin-top:14px}
details li{margin:2px 0}
.fail{padding:10px;border:1px dashed var(--line);color:var(--mut)}
footer{margin-top:28px;font-size:12px;color:var(--mut);text-align:center}
"""


def render_section(sec, results):
    body = []
    for text, sources in results:
        if text is None:
            body.append('<p class="fail">This part could not be generated today (API limit or error). It will retry tomorrow.</p>')
            continue
        body.append(md_to_html(text))
        if sources:
            lis = "".join(f'<li><a target="_blank" rel="noopener" href="{html.escape(u)}">{html.escape(t)}</a></li>'
                          for t, u in sources[:25])
            body.append(f"<details><summary>Sources searched ({len(sources)})</summary><ul>{lis}</ul></details>")
    return f'<section id="{sec["id"]}"><h2>{html.escape(sec["title"])}</h2>\n' + "\n".join(body) + "</section>"


def render_page(sections_html, nav, date_str):
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Daily Newspaper - {date_str}</title><style>{CSS}</style></head>
<body><div class="wrap">
<header><h1>VAIBHAV'S DAILY NEWSPAPER</h1><div class="date">{date_str} &middot; India &amp; World &middot; Morning Edition</div></header>
<nav>{nav}</nav>
{sections_html}
<footer>AI-generated from web search. Always check the original source before quoting numbers.<br>
<a href="archive.html">Past editions</a></footer>
</div></body></html>"""


def build_archive(docs):
    files = sorted([p.name for p in docs.glob("20*.html")], reverse=True)
    li = "\n".join(f'<li><a href="{f}">{f[:-5]}</a></li>' for f in files)
    (docs / "archive.html").write_text(
        f"<!doctype html><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>Archive</title><style>{CSS}</style><div class='wrap'><header><h1>ARCHIVE</h1></header>"
        f"<ul>{li}</ul><p><a href='index.html'>Back to today</a></p></div>", encoding="utf-8")


def main():
    if not API_KEY:
        sys.exit("GEMINI_API_KEY is missing. Add it under Settings > Secrets and variables > Actions.")
    now = datetime.datetime.now(IST)
    date_str = now.strftime("%A, %d %B %Y")
    sections_html, nav, ok = [], [], 0
    first = True
    for sec in SECTIONS:
        results = []
        for prompt in sec["prompts"]:
            if not first:
                time.sleep(PAUSE)
            first = False
            print(f"Generating: {sec['title']} ...")
            text, sources = gemini(prompt, date_str)
            ok += text is not None
            results.append((text, sources))
        sections_html.append(render_section(sec, results))
        nav.append(f'<a href="#{sec["id"]}">{html.escape(sec["title"].split(":")[0])}</a>')
    if ok == 0:
        sys.exit("Every section failed. Not publishing an empty edition.")
    page = render_page("\n".join(sections_html), "".join(nav), date_str)
    docs = pathlib.Path("docs")
    docs.mkdir(exist_ok=True)
    (docs / "index.html").write_text(page, encoding="utf-8")
    (docs / f"{now:%Y-%m-%d}.html").write_text(page, encoding="utf-8")
    build_archive(docs)
    print(f"Edition built: {ok} parts generated.")


if __name__ == "__main__":
    main()
