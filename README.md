# Facette — Website

Official website for **Facette** — honest 5-minute brain training for iPhone, iPad & Mac.
Calm, private, no tracking. 30 short games across 12 cognitive areas.

🌐 **https://facette.life**

## Pages
- [`index.html`](index.html) — Home (app overview, features, honest positioning)
- [`eula.html`](eula.html) — Terms of Use / End-User License Agreement (EULA)
- [`privacy.html`](privacy.html) — Privacy Policy (GDPR, local-first)

Static, fully self-contained HTML (no external CSS/JS/fonts), served via **GitHub Pages**.
`.nojekyll` is present so the files are served exactly as-is.

## Serve under the custom domain `facette.life`
1. Repo **Settings → Pages → Custom domain** → enter `facette.life` (creates a `CNAME` file).
2. At your DNS registrar:
   - Root `facette.life`: four **A** records → `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`
   - `www` → **CNAME** → `randyp007.github.io`
3. Enable **Enforce HTTPS**.

Detailed guide: see `docs/Website-GoogleSites-Anleitung.md` in the app repository.

## Contact
- General: **feedback@facette.life**
- Privacy: **privacy@facette.life**

## Provider
Andreas Putzinger, Austria. Full postal address available on request.

---
Part of the Facette project · app repository: <https://github.com/randyp007/facette>
