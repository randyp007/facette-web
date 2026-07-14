#!/usr/bin/env python3
"""
Facette — Tagesspruch-Generator fuer facette.life (Content-Engine, Teil 1).

Erzeugt deterministisch (nach Tag-des-Jahres) die "Spruch des Tages"-Seite in EN + DE
aus den 200 kuratierten, zweisprachigen Spruechen — mit sauberem SEO (Title, Meta,
Canonical, hreflang en<->de, JSON-LD CreativeWork, Open Graph). Gedacht als taeglicher
Cron-Job:  python3 tools/site/gen_quote.py && git add -A && git commit -m "quote" && git push

- Seiten:  website/en/quote.html, website/de/quote.html, website/quote.html (EN-Canonical)
- Archiv:  website/quotes/index.html  (bewusst NOINDEX -> Thin-/Scaled-Content-Schutz)
- Ein per-Tag SVG-Share-Card wird erzeugt; OG-Image faellt bis zur PNG-Rasterung auf ein
  vorhandenes Marken-PNG zurueck (rsvg-convert/cairosvg im Cron -> echtes PNG moeglich).

Optionen:  --day N   (Tag-des-Jahres erzwingen, fuer Tests/Determinismus)
           --root P  (Website-Wurzel, Default: ../../website relativ zu diesem Skript)
"""
import json, os, sys, argparse, html, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DEF_ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
QUOTES = os.path.join(HERE, "quotes.json")
SITE = "https://facette.life"
OG_FALLBACK = f"{SITE}/shots/home.png"

STYLE = """
:root{--canvas:#F6F7F9;--surface:#FFFFFF;--sunken:#ECEFF3;--hairline:#DDE2E9;
--ink:#14181F;--ink2:#5A6373;--amber:#F5A623;--gold:#FFD27A;--deepgold:#C8821E;--glow:#FFF6E6;
--serif:ui-serif,"New York",Georgia,"Times New Roman",serif;
--sans:-apple-system,BlinkMacSystemFont,"SF Pro Text",system-ui,"Segoe UI",Roboto,sans-serif;}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;font-family:var(--sans);background:var(--canvas);color:var(--ink);line-height:1.62;-webkit-font-smoothing:antialiased}
h1,h2,.serif{font-family:var(--serif);font-weight:600;letter-spacing:-.01em}
a{color:var(--deepgold)}a:hover{color:var(--amber)}
.langbar{display:flex;gap:2px;justify-content:center;flex-wrap:wrap;background:#0C0F14;border-bottom:1px solid #2A313D;padding:7px 8px}
.langbar a{color:#9AA4B2;text-decoration:none;font-family:var(--sans);font-size:12.5px;font-weight:600;letter-spacing:.03em;padding:4px 9px;border-radius:7px}
.langbar a:hover{color:#FFD27A;background:#161A22}.langbar a.on{color:#0C0F14;background:#F5A623}
.topbar{border-bottom:1px solid var(--hairline);background:var(--surface)}
.topbar .wrap{max-width:760px;margin:0 auto;padding:16px 24px;display:flex;align-items:center;justify-content:space-between}
.brandline{display:flex;align-items:center;gap:12px}
.funke{width:12px;height:12px;border-radius:50%;background:var(--gold);box-shadow:0 0 18px 4px rgba(255,210,122,.7)}
.logoname{font-family:var(--serif);font-size:22px;font-weight:600;letter-spacing:.02em}
.back{font-size:14px;font-weight:600;text-decoration:none;color:var(--ink2)}.back:hover{color:var(--ink)}
.read{max-width:760px;margin:0 auto;padding:56px 24px 24px;text-align:center}
.eyebrow{font-weight:700;font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--amber);margin:0}
.card{background:var(--surface);border:1px solid var(--hairline);border-radius:22px;padding:48px 32px;margin:26px 0 20px;
box-shadow:0 1px 0 rgba(20,24,31,.02),0 22px 48px -30px rgba(20,24,31,.28)}
.quote{font-family:var(--serif);font-size:clamp(26px,5vw,40px);line-height:1.18;margin:0;color:var(--ink);text-wrap:balance}
.datel{font-size:13px;color:var(--ink2);margin:0 0 4px;letter-spacing:.02em}
.cta{display:inline-block;margin-top:8px;background:var(--amber);color:#1a1204;font-weight:700;text-decoration:none;
padding:13px 22px;border-radius:12px;box-shadow:0 10px 24px -12px rgba(245,166,35,.9)}
.cta:hover{background:var(--gold);color:#1a1204}
.sub{color:var(--ink2);font-size:16px;max-width:52ch;margin:18px auto 0}
footer{border-top:1px solid var(--hairline);margin-top:40px;background:var(--surface)}
footer .wrap{max-width:760px;margin:0 auto;padding:26px 24px;display:flex;flex-wrap:wrap;gap:6px 16px;
align-items:center;justify-content:space-between;font-size:13.5px;color:var(--ink2)}
footer a{color:var(--ink2)}footer a:hover{color:var(--ink)}
@media(max-width:640px){.card{padding:36px 22px}.read{padding-top:38px}}
"""

L = {
 "en": dict(lang="en", eyebrow="Quote of the day", date_fmt="%B %-d, %Y",
   title="Quote of the day — Facette", back="← facette.life",
   sub="A calm, ad-free five minutes for your mind. 20+ short brain games that adapt to you — on iPhone, iPad and Mac.",
   cta="Get Facette", home=f"{SITE}/en/index.html", archive_h="All quotes"),
 "de": dict(lang="de", eyebrow="Spruch des Tages", date_fmt="%-d. %B %Y",
   title="Spruch des Tages — Facette", back="← facette.life",
   sub="Fünf ruhige, werbefreie Minuten für deinen Kopf. 20+ kurze Denkspiele, die sich dir anpassen — auf iPhone, iPad und Mac.",
   cta="Facette holen", home=f"{SITE}/de/index.html", archive_h="Alle Sprüche"),
}
MONTHS_DE = ["Januar","Februar","März","April","Mai","Juni","Juli","August","September","Oktober","November","Dezember"]

def esc(s): return html.escape(s, quote=True)

def fmt_date(d, lang):
    if lang == "de": return f"{d.day}. {MONTHS_DE[d.month-1]} {d.year}"
    return d.strftime("%B ") + f"{d.day}, {d.year}"

def page(lang, q, d, appstore_id="6786462068"):
    cfg = L[lang]
    text = q[lang]
    date_str = fmt_date(d, lang)
    canonical = f"{SITE}/{lang}/quote.html"
    alt = "de" if lang == "en" else "en"
    meta_desc = (text[:150]).replace('"', "'")
    jsonld = {
      "@context": "https://schema.org", "@type": "CreativeWork", "name": cfg["title"],
      "text": text, "inLanguage": lang, "datePublished": d.isoformat(), "isPartOf": SITE,
      "publisher": {"@type": "Organization", "name": "Facette", "url": SITE},
    }
    en_on = ' class="on"' if lang == "en" else ""
    de_on = ' class="on"' if lang == "de" else ""
    langbar = ('<nav class="langbar" aria-label="Language">'
               f'<a href="/en/quote.html"{en_on}>EN</a>'
               f'<a href="/de/quote.html"{de_on}>DE</a></nav>')
    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(cfg['title'])}</title>
<meta name="description" content="{esc(meta_desc)}">
<link rel="canonical" href="{canonical}">
<link rel="alternate" hreflang="en" href="{SITE}/en/quote.html">
<link rel="alternate" hreflang="de" href="{SITE}/de/quote.html">
<link rel="alternate" hreflang="x-default" href="{SITE}/quote.html">
<meta name="apple-itunes-app" content="app-id={appstore_id}">
<meta property="og:type" content="website">
<meta property="og:title" content="{esc(cfg['title'])}">
<meta property="og:description" content="{esc(meta_desc)}">
<meta property="og:image" content="{OG_FALLBACK}">
<meta property="og:url" content="{canonical}">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>
<style>{STYLE}</style>
</head>
<body>
{langbar}
<header class="topbar"><div class="wrap">
  <div class="brandline"><span class="funke" aria-hidden="true"></span><span class="logoname">Facette</span></div>
  <a class="back" href="{cfg['home']}">{esc(cfg['back'])}</a>
</div></header>
<main class="read">
  <p class="eyebrow">{esc(cfg['eyebrow'])}</p>
  <div class="card">
    <p class="datel">{esc(date_str)}</p>
    <blockquote class="quote">{esc(text)}</blockquote>
  </div>
  <a class="cta" href="https://apps.apple.com/app/id{appstore_id}">{esc(cfg['cta'])}</a>
  <p class="sub">{esc(cfg['sub'])}</p>
</main>
<footer><div class="wrap">
  <span>&copy; {d.year} Facette &middot; Andreas Putzinger, Austria</span>
  <span><a href="{cfg['home']}">Home</a> &middot; <a href="/{lang}/privacy.html">Privacy</a></span>
</div></footer>
</body>
</html>
"""

def svg_card(lang, q, d):
    text = q[lang]
    # simple, on-brand 1200x630 share card (rasterize later via rsvg-convert/cairosvg in cron)
    wrapped = text if len(text) < 60 else text
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
<rect width="1200" height="630" fill="#0C0F14"/>
<circle cx="120" cy="110" r="13" fill="#FFD27A"/>
<text x="150" y="120" font-family="Georgia, 'New York', serif" font-size="34" fill="#EDF1F8">Facette</text>
<text x="120" y="200" font-family="-apple-system, sans-serif" font-size="20" letter-spacing="4" fill="#F5A623">{esc(("SPRUCH DES TAGES" if lang=="de" else "QUOTE OF THE DAY"))}</text>
<foreignObject x="110" y="240" width="980" height="280">
<div xmlns="http://www.w3.org/1999/xhtml" style="font-family:Georgia,'New York',serif;font-size:52px;line-height:1.2;color:#F3ECDA">{esc(text)}</div>
</foreignObject>
<text x="120" y="580" font-family="-apple-system, sans-serif" font-size="22" fill="#9AA4B2">{esc(("Fünf Minuten für deinen Kopf · werbefrei" if lang=="de" else "Five minutes for your mind · ad-free"))}</text>
</svg>"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--day", type=int, default=None, help="Tag-des-Jahres erzwingen (1-366)")
    ap.add_argument("--root", default=DEF_ROOT)
    args = ap.parse_args()

    data = json.load(open(QUOTES, encoding="utf-8"))
    quotes = data["quotes"]
    today = datetime.date.today()
    yday = args.day if args.day else today.timetuple().tm_yday
    q = quotes[(yday - 1) % len(quotes)]

    written = []
    for lang in ("en", "de"):
        p = os.path.join(args.root, lang, "quote.html")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w", encoding="utf-8").write(page(lang, q, today))
        written.append(os.path.relpath(p, args.root))
        # svg share card
        cardp = os.path.join(args.root, "quote", f"card-{lang}.svg")
        os.makedirs(os.path.dirname(cardp), exist_ok=True)
        open(cardp, "w", encoding="utf-8").write(svg_card(lang, q, today))
    # root canonical = English
    rp = os.path.join(args.root, "quote.html")
    open(rp, "w", encoding="utf-8").write(page("en", q, today))
    written.append("quote.html")

    print(f"Spruch #{q['id']} (Tag {yday}): \"{q['en']}\"")
    print("Geschrieben:", ", ".join(written))
    print("Hinweis: OG-Image-PNG faellt auf shots/home.png zurueck; per-Tag-SVG in website/quote/card-*.svg")
    print("         (Cron kann via rsvg-convert/cairosvg das SVG zu einem 1200x630-PNG rastern.)")

if __name__ == "__main__":
    main()
