"""Παράγει τις σελίδες του site από τα info.json.

Δομή:
  site.json                 γενικές ρυθμίσεις
  <slug>/info.json          στοιχεία εταιρείας + λίστα δημοσιεύσεων
  <slug>/*.pdf              τα αρχεία
Τρέξιμο:  python -I build.py
"""
import html
import json
import os
from datetime import date

ROOT = os.path.dirname(os.path.abspath(__file__))

CSS = """
:root{--bg:#f6f7f9;--card:#fff;--text:#1d2330;--muted:#5d6675;--line:#e2e5ea;--accent:#1f5fa8;--accent-bg:#eaf1fa}
@media (prefers-color-scheme:dark){:root{--bg:#14171c;--card:#1c2027;--text:#e6e8ec;--muted:#9aa3b0;--line:#2c323c;--accent:#79acec;--accent-bg:#1e2a3a}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:16px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif}
.wrap{max-width:860px;margin:0 auto;padding:32px 16px 48px}
header h1{font-size:1.6rem;margin:0 0 4px;line-height:1.25}
header p{margin:0;color:var(--muted)}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:20px;margin-top:24px}
dl{display:grid;grid-template-columns:max-content 1fr;gap:6px 18px;margin:0}
dt{color:var(--muted)}dd{margin:0;font-weight:500}
h2{font-size:1.1rem;margin:0 0 12px}
table{width:100%;border-collapse:collapse}
th,td{text-align:left;padding:10px 8px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:.85rem;color:var(--muted);font-weight:600}
tr:last-child td{border-bottom:0}
a{color:var(--accent)}
a.pdf{display:inline-block;padding:4px 10px;border-radius:6px;background:var(--accent-bg);text-decoration:none;font-weight:600;white-space:nowrap}
.small{font-size:.85rem;color:var(--muted)}
ul.clients{list-style:none;padding:0;margin:0}ul.clients li{padding:8px 0;border-bottom:1px solid var(--line)}ul.clients li:last-child{border-bottom:0}
footer{margin-top:32px;font-size:.85rem;color:var(--muted)}
@media (max-width:560px){dl{grid-template-columns:1fr;gap:0}dd{margin-bottom:8px}th.hide,td.hide{display:none}}
"""

e = html.escape


def page(title, body, description=""):
    return f"""<!doctype html>
<html lang="el">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(description)}">
<style>{CSS}</style>
</head>
<body><div class="wrap">
{body}
</div></body>
</html>
"""


def fmt_date(s):
    try:
        y, m, d = s.split("-")
        return f"{d}/{m}/{y}"
    except Exception:
        return s or ""


def money(v):
    s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{s} €"


def fmt_size(path):
    try:
        n = os.path.getsize(path)
    except OSError:
        return ""
    return f"{n / 1024:.0f} KB" if n < 1024 * 1024 else f"{n / 1024 / 1024:.1f} MB"


def build_client(slug, info, site):
    d = os.path.join(ROOT, slug)
    rows = []
    for f in sorted(info.get("filings", []), key=lambda x: str(x.get("year", "")), reverse=True):
        fpath = os.path.join(d, f["file"])
        if not os.path.exists(fpath):
            raise SystemExit(f"Λείπει το αρχείο: {slug}/{f['file']}")
        rows.append(
            "<tr>"
            f"<td><strong>{e(str(f.get('year', '')))}</strong><div class='small'>{e(f.get('period', ''))}</div></td>"
            f"<td>{e(f.get('title', 'Οικονομικές καταστάσεις'))}</td>"
            f"<td class='hide'>{e(fmt_date(f.get('posted', '')))}</td>"
            f"<td><a class='pdf' href='{e(f['file'])}' target='_blank' rel='noopener'>PDF</a>"
            f"<div class='small'>{fmt_size(fpath)}</div></td>"
            "</tr>"
        )
    # Στοιχεία κατά το άρθρο 47 ν. 4072/2012 (εταιρική διαφάνεια)
    facts = [("Επωνυμία", info.get("name")), ("Διακριτικός τίτλος", info.get("distinctive_title")),
             ("Αρ. ΓΕΜΗ", info.get("gemi")), ("ΑΦΜ", info.get("afm")),
             ("Έδρα / Διεύθυνση", info.get("address") or info.get("seat")),
             ("Εταιρικό κεφάλαιο", money(info["capital"]) if "capital" in info else None),
             ("Εγγυητικές εισφορές", money(info["guarantee"]) if "guarantee" in info else None),
             ("Κατάσταση", info.get("status")),
             ("Διαχείριση", ", ".join(info.get("managers", [])))]
    dl = "".join(f"<dt>{k}</dt><dd>{e(v)}</dd>" for k, v in facts if v)
    table = (
        "<table><thead><tr><th>Χρήση</th><th>Έγγραφο</th><th class='hide'>Ανάρτηση</th><th>Αρχείο</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>" if rows else "<p class='small'>Δεν υπάρχουν ακόμη αναρτήσεις.</p>"
    )
    partners = ""
    if info.get("partners"):
        prow = "".join(f"<tr><td>{e(p['name'])}</td><td>{e(p['pct_label'])}</td><td>{money(p['amount'])}</td></tr>"
                       for p in info["partners"])
        partners = ("<section class='card'><h2>Εταίροι και εισφορές</h2><table><thead><tr><th>Εταίρος</th>"
                    "<th>Ποσοστό</th><th>Κεφαλαιακή εισφορά</th></tr></thead>"
                    f"<tbody>{prow}</tbody></table></section>")
    body = f"""<header><h1>{e(info['name'])}</h1><p>Εταιρικά στοιχεία και οικονομικές καταστάσεις</p></header>
<section class="card"><h2>Στοιχεία εταιρείας</h2><dl>{dl}</dl></section>
{partners}
<section class="card"><h2>Δημοσιευμένες οικονομικές καταστάσεις</h2>{table}</section>
<footer>Τελευταία ενημέρωση: {date.today().strftime('%d/%m/%Y')}</footer>"""
    with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(page(f"{info['name']} – Οικονομικές καταστάσεις", body,
                      f"Οικονομικές καταστάσεις {info['name']}"))


def main():
    with open(os.path.join(ROOT, "site.json"), encoding="utf-8") as fh:
        site = json.load(fh)
    clients = []
    for slug in sorted(os.listdir(ROOT)):
        p = os.path.join(ROOT, slug, "info.json")
        if os.path.isfile(p):
            with open(p, encoding="utf-8") as fh:
                info = json.load(fh)
            build_client(slug, info, site)
            clients.append((slug, info))
            print(f"  {site['base_url']}/{slug}/")
    listing = ""
    if site.get("list_clients") and clients:
        items = "".join(f"<li><a href='{e(s)}/'>{e(i['name'])}</a></li>" for s, i in
                        sorted(clients, key=lambda c: c[1]["name"]))
        listing = f"<section class='card'><h2>Εταιρείες</h2><ul class='clients'>{items}</ul></section>"
    body = f"""<header><h1>{e(site['title'])}</h1><p>{e(site.get('subtitle', ''))}</p></header>
{listing}"""
    with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(page(site["title"], body, site.get("subtitle", "")))
    # Τοπική λίστα links για το ΓΕΜΗ (στο .gitignore, δεν δημοσιεύεται)
    rows = sorted(clients, key=lambda c: c[1]["name"])
    with open(os.path.join(ROOT, "LINKS-GEMH.txt"), "w", encoding="utf-8-sig", newline="\r\n") as fh:
        fh.write("LINKS ΔΗΜΟΣΙΕΥΣΗΣ ΟΙΚΟΝΟΜΙΚΩΝ ΚΑΤΑΣΤΑΣΕΩΝ (για δήλωση στο ΓΕΜΗ)\n")
        fh.write(f"Ενημέρωση: {date.today().strftime('%d/%m/%Y')} – {len(rows)} εταιρείες\n\n")
        for n, (slug, info) in enumerate(rows, 1):
            fh.write(f"{n:2}. {info['name']}\n    ΓΕΜΗ: {info.get('gemi', '')}   ΑΦΜ: {info.get('afm', '')}\n"
                     f"    {site['base_url']}/{slug}/\n\n")
    print(f"OK – {len(clients)} εταιρείες")


if __name__ == "__main__":
    main()
