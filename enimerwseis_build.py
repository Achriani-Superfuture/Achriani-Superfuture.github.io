"""Παράγει τη σελίδα ενημερώσεων πελατών (φάκελος enimerwseis/).

Δομή:
  enimerwseis/settings.json        τίτλος σελίδας + κατηγορίες
  enimerwseis/keimena/*.md         μία ενημέρωση ανά αρχείο
  enimerwseis/arxeia/*             συνημμένα (PDF κλπ)
Παράγει:
  enimerwseis/index.html           λίστα με φίλτρο κατηγοριών
  enimerwseis/<όνομα-αρχείου>/     σελίδα κάθε ενημέρωσης

Μορφή αρχείου ενημέρωσης:
  ---
  τίτλος: ...
  ημερομηνία: 2026-11-09
  κατηγορία: forologika
  σημαντικό: ναι                (προαιρετικό)
  προθεσμία: 2026-11-30         (προαιρετικό)
  περίληψη: ...                 (προαιρετικό)
  συνημμένα: odigos.pdf, entypo.pdf   (προαιρετικό, από τον φάκελο arxeia/)
  ---
  Κείμενο. Κενή γραμμή = νέα παράγραφος.
  ## Υπότιτλος
  - λίστα
  **έντονα**, [κείμενο](https://link)
  > πλαίσιο που ξεχωρίζει
"""
import html
import json
import os
import re
import shutil
import unicodedata

e = html.escape

CSS = """
.chips{display:flex;flex-wrap:wrap;gap:8px}
.chip{--c:var(--accent);font:inherit;font-size:.9rem;padding:6px 12px;border-radius:999px;border:1px solid var(--line);background:var(--card);color:var(--text);cursor:pointer}
.chip::before{content:"";display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--c);margin-right:7px;vertical-align:1px}
.chip.all::before{display:none}
.chip[aria-pressed=true]{border-color:var(--c);background:color-mix(in srgb,var(--c) 14%,var(--card));font-weight:600}
.search{width:100%;margin-top:14px;font:inherit;padding:9px 12px;border-radius:8px;border:1px solid var(--line);background:var(--bg);color:var(--text)}
.post{display:block}
.post h3{margin:6px 0 6px;font-size:1.12rem;line-height:1.35}
.post h3 a{color:var(--text);text-decoration:none}.post h3 a:hover{color:var(--accent)}
.post p{margin:0;color:var(--muted)}
.meta{display:flex;flex-wrap:wrap;align-items:center;gap:6px 10px;font-size:.85rem;color:var(--muted)}
.badge{--c:var(--accent);display:inline-block;padding:2px 9px;border-radius:999px;font-size:.78rem;font-weight:600;color:var(--c);background:color-mix(in srgb,var(--c) 13%,transparent)}
.badge.imp{--c:#c0392b}.badge.new{--c:#1e8449}
.dl{font-size:.85rem;margin-top:8px;color:var(--text)}
.post.imp{border-left:4px solid #c0392b}
ul.deadlines{list-style:none;padding:0;margin:0}
ul.deadlines li{display:flex;gap:14px;padding:8px 0;border-bottom:1px solid var(--line)}ul.deadlines li:last-child{border-bottom:0}
ul.deadlines .d{font-weight:700;min-width:92px}
.callout{border-left:4px solid var(--accent);background:var(--accent-bg);padding:12px 16px;border-radius:6px;margin:14px 0}
.callout.warn{border-color:#c0392b;background:color-mix(in srgb,#c0392b 10%,var(--card))}
.body h2{font-size:1.15rem;margin:22px 0 8px}.body h3{font-size:1rem;margin:18px 0 6px}
.body p{margin:0 0 12px}.body ul,.body ol{margin:0 0 12px;padding-left:22px}.body li{margin:3px 0}
.body>:first-child{margin-top:0}.body>:last-child{margin-bottom:0}
.back{display:inline-block;margin-bottom:14px;text-decoration:none;font-size:.9rem}
.btn{font:inherit;font-size:.85rem;padding:6px 12px;border-radius:6px;border:1px solid var(--line);background:var(--card);color:var(--text);cursor:pointer}
.empty{text-align:center;color:var(--muted)}
[hidden]{display:none!important}
"""

GR_MONTHS = ["Ιανουαρίου", "Φεβρουαρίου", "Μαρτίου", "Απριλίου", "Μαΐου", "Ιουνίου", "Ιουλίου",
             "Αυγούστου", "Σεπτεμβρίου", "Οκτωβρίου", "Νοεμβρίου", "Δεκεμβρίου"]


def long_date(s):
    try:
        y, m, d = s.split("-")
        return f"{int(d)} {GR_MONTHS[int(m) - 1]} {y}"
    except Exception:
        return s


def short_date(s):
    try:
        y, m, d = s.split("-")
        return f"{d}/{m}/{y}"
    except Exception:
        return s


def plain(s):
    """Πεζά χωρίς τόνους (για κλειδιά και αναζήτηση)."""
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


KEYS = {"τιτλος": "title", "ημερομηνια": "date", "κατηγορια": "cat", "σημαντικο": "important",
        "προθεσμια": "deadline", "περιληψη": "summary", "συνημμενα": "files",
        "title": "title", "date": "date", "category": "cat", "important": "important",
        "deadline": "deadline", "summary": "summary", "files": "files"}


def parse_post(path):
    with open(path, encoding="utf-8-sig") as fh:
        text = fh.read().replace("\r\n", "\n")
    meta, body = {}, text
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if m:
        for line in m.group(1).split("\n"):
            if ":" in line:
                k, v = line.split(":", 1)
                key = KEYS.get(plain(k.strip()))
                if key:
                    meta[key] = v.strip()
        body = m.group(2)
    slug = os.path.splitext(os.path.basename(path))[0]
    if "date" not in meta:
        dm = re.match(r"(\d{4}-\d{2}-\d{2})", slug)
        meta["date"] = dm.group(1) if dm else ""
    meta["important"] = plain(meta.get("important", "")) in ("ναι", "nai", "yes", "1", "true")
    meta["files"] = [f.strip() for f in meta.get("files", "").split(",") if f.strip()]
    meta["slug"] = slug
    meta["body"] = body
    return meta


def inline(s):
    s = e(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)",
               lambda m: f'<a href="{e(m.group(2))}" target="_blank" rel="noopener">{m.group(1)}</a>', s)
    s = re.sub(r'(?<!href=")(?<!">)(https?://[^\s<]+)', r'<a href="\1" target="_blank" rel="noopener">\1</a>', s)
    return s


def markdown(text):
    out, para, lst, lst_tag, quote = [], [], [], None, []

    def flush():
        nonlocal para, lst, lst_tag, quote
        if para:
            out.append("<p>" + "<br>".join(inline(x) for x in para) + "</p>")
        if lst:
            out.append(f"<{lst_tag}>" + "".join(f"<li>{inline(x)}</li>" for x in lst) + f"</{lst_tag}>")
        if quote:
            warn = quote[0].startswith("!")
            if warn:
                quote[0] = quote[0][1:].strip()
            out.append(f"<div class='callout{' warn' if warn else ''}'>" + "<br>".join(inline(x) for x in quote) + "</div>")
        para, lst, lst_tag, quote = [], [], None, []

    for raw in text.split("\n"):
        line = raw.strip()
        if not line:
            flush()
        elif line.startswith("### "):
            flush(); out.append(f"<h3>{inline(line[4:])}</h3>")
        elif line.startswith("## ") or line.startswith("# "):
            flush(); out.append(f"<h2>{inline(line.split(' ', 1)[1])}</h2>")
        elif line.startswith(">"):
            if para or lst:
                flush()
            quote.append(line[1:].strip())
        elif re.match(r"^[-*•] ", line) or re.match(r"^\d+[.)] ", line):
            tag = "ul" if re.match(r"^[-*•] ", line) else "ol"
            if para or quote or (lst and lst_tag != tag):
                flush()
            lst_tag = tag
            lst.append(line.split(" ", 1)[1])
        else:
            if lst or quote:
                flush()
            para.append(line)
    flush()
    return "\n".join(out)


def build(root, page):
    d = os.path.join(root, "enimerwseis")
    src = os.path.join(d, "keimena")
    if not os.path.isdir(src):
        return
    with open(os.path.join(d, "settings.json"), encoding="utf-8") as fh:
        st = json.load(fh)
    cats = {c["key"]: c for c in st["categories"]}

    posts = []
    for fn in os.listdir(src):
        if fn.lower().endswith(".md"):
            p = parse_post(os.path.join(src, fn))
            if p.get("cat") not in cats:
                raise SystemExit(f"Ενημέρωση {fn}: άγνωστη κατηγορία «{p.get('cat', '')}». "
                                 f"Επιτρέπονται: {', '.join(cats)}")
            if not p.get("title"):
                raise SystemExit(f"Ενημέρωση {fn}: λείπει ο τίτλος")
            for f in p["files"]:
                if not os.path.isfile(os.path.join(d, "arxeia", f)):
                    raise SystemExit(f"Ενημέρωση {fn}: λείπει το συνημμένο arxeia/{f}")
            posts.append(p)
    posts.sort(key=lambda p: (p["date"], p["slug"]), reverse=True)

    # Καθάρισμα παλιών σελίδων (φάκελοι που δεν αντιστοιχούν πια σε ενημέρωση)
    keep = {p["slug"] for p in posts} | {"keimena", "arxeia"}
    for name in os.listdir(d):
        full = os.path.join(d, name)
        if os.path.isdir(full) and name not in keep and os.path.isfile(os.path.join(full, "index.html")):
            shutil.rmtree(full)

    def badge(cat):
        c = cats[cat]
        return f"<span class='badge' style='--c:{e(c['color'])}'>{e(c['label'])}</span>"

    # --- Σελίδα κάθε ενημέρωσης ---
    for p in posts:
        meta = [f"<span>{long_date(p['date'])}</span>", badge(p["cat"])]
        if p["important"]:
            meta.append("<span class='badge imp'>Σημαντικό</span>")
        deadline = (f"<div class='callout warn'><strong>Προθεσμία: {long_date(p['deadline'])}</strong></div>"
                    if p.get("deadline") else "")
        files = ""
        if p["files"]:
            items = "".join(
                f"<li><a class='pdf' href='../arxeia/{e(f)}' target='_blank' rel='noopener'>{e(f)}</a></li>"
                for f in p["files"])
            files = (f"<section class='card'><h2>Συνημμένα</h2>"
                     f"<ul class='clients'>{items}</ul></section>")
        body = f"""<a class="back" href="../">← Όλες οι ενημερώσεις</a>
<header><h1>{e(p['title'])}</h1><div class="meta" style="margin-top:8px">{''.join(meta)}</div></header>
{deadline}
<section class="card body">{markdown(p['body'])}</section>
{files}
<footer><button class="btn" id="copy">Αντιγραφή συνδέσμου</button> · {e(st['title'])}</footer>
<script>
document.getElementById('copy').onclick=function(){{var b=this;navigator.clipboard.writeText(location.href).then(function(){{b.textContent='Αντιγράφηκε ✓'}})}};
</script>"""
        desc = p.get("summary") or ""
        og = (f'<meta property="og:title" content="{e(p["title"])}">'
              f'<meta property="og:description" content="{e(desc)}">'
              f'<meta property="og:type" content="article">')
        out = os.path.join(d, p["slug"])
        os.makedirs(out, exist_ok=True)
        with open(os.path.join(out, "index.html"), "w", encoding="utf-8") as fh:
            fh.write(page(f"{p['title']} – {st['title']}", body, desc, extra_css=CSS, head_extra=og))

    # --- Αρχική σελίδα ενημερώσεων ---
    chips = "<button class='chip all' data-k='' aria-pressed='true'>Όλες</button>" + "".join(
        f"<button class='chip' data-k='{e(k)}' style='--c:{e(c['color'])}' aria-pressed='false'>{e(c['label'])}</button>"
        for k, c in cats.items())
    cards, dls = [], []
    for p in posts:
        search = plain(" ".join([p["title"], p.get("summary", ""), cats[p["cat"]]["label"], p["body"]]))
        extra = "<span class='badge imp'>Σημαντικό</span>" if p["important"] else ""
        dl = f"<div class='dl'>⏰ Προθεσμία: <strong>{short_date(p['deadline'])}</strong></div>" if p.get("deadline") else ""
        summ = f"<p>{e(p['summary'])}</p>" if p.get("summary") else ""
        cards.append(
            f"<article class='card post{' imp' if p['important'] else ''}' data-cat='{e(p['cat'])}' "
            f"data-date='{e(p['date'])}' data-q='{e(search)}'>"
            f"<div class='meta'><span>{short_date(p['date'])}</span>{badge(p['cat'])}{extra}"
            f"<span class='badge new' hidden>Νέο</span></div>"
            f"<h3><a href='{e(p['slug'])}/'>{e(p['title'])}</a></h3>{summ}{dl}</article>")
        if p.get("deadline"):
            dls.append((p["deadline"], p))
    dls.sort(key=lambda x: x[0])
    dl_items = "".join(
        f"<li data-cat='{e(p['cat'])}' data-deadline='{e(dd)}'><span class='d'>{short_date(dd)}</span>"
        f"<a href='{e(p['slug'])}/'>{e(p['title'])}</a></li>" for dd, p in dls)

    body = f"""<header><h1>{e(st['title'])}</h1><p>{e(st.get('subtitle', ''))}</p></header>
<section class="card"><h2>Τι σας ενδιαφέρει;</h2>
<div class="chips" id="chips">{chips}</div>
<input class="search" id="q" type="search" placeholder="Αναζήτηση…" aria-label="Αναζήτηση">
<p class="small" style="margin:10px 0 0">Η επιλογή σας θυμάται σε αυτή τη συσκευή.</p></section>
<section class="card" id="dls" hidden><h2>Προσεχείς προθεσμίες</h2><ul class="deadlines">{dl_items}</ul></section>
<div id="list">{''.join(cards)}</div>
<section class="card empty" id="empty" hidden>Δεν υπάρχουν ενημερώσεις για αυτή την επιλογή.</section>
<footer>{e(st.get('footer', ''))}</footer>
<script>
(function(){{
var KEY='enim-cats',LAST='enim-last',sel=[];
function get(k){{try{{return localStorage.getItem(k)}}catch(_){{return null}}}}
function put(k,v){{try{{localStorage.setItem(k,v)}}catch(_){{}}}}
function norm(s){{return s.toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g,'')}}
var url=new URLSearchParams(location.search).get('k');
if(url!==null){{sel=url.split(',').filter(Boolean);put(KEY,sel.join(','))}}else{{sel=(get(KEY)||'').split(',').filter(Boolean)}}
var t=new Date(),today=t.getFullYear()+'-'+String(t.getMonth()+1).padStart(2,'0')+'-'+String(t.getDate()).padStart(2,'0');
var last=get(LAST);
if(last)document.querySelectorAll('.post').forEach(function(a){{if(a.dataset.date>last)a.querySelector('.badge.new').hidden=false}});
put(LAST,today);
var chips=document.querySelectorAll('.chip'),q=document.getElementById('q');
function show(cat){{return !sel.length||sel.indexOf(cat)>=0}}
function render(){{
  chips.forEach(function(c){{var k=c.dataset.k;c.setAttribute('aria-pressed',String(k?sel.indexOf(k)>=0:!sel.length))}});
  var s=norm(q.value.trim()),n=0;
  document.querySelectorAll('.post').forEach(function(a){{var ok=show(a.dataset.cat)&&(!s||a.dataset.q.indexOf(s)>=0);a.hidden=!ok;if(ok)n++}});
  document.getElementById('empty').hidden=n>0;
  var m=0;document.querySelectorAll('#dls li').forEach(function(li){{var ok=li.dataset.deadline>=today&&show(li.dataset.cat);li.hidden=!ok;if(ok)m++}});
  document.getElementById('dls').hidden=m===0;
}}
chips.forEach(function(c){{c.onclick=function(){{var k=c.dataset.k;
  if(!k)sel=[];else{{var i=sel.indexOf(k);if(i>=0)sel.splice(i,1);else sel.push(k)}}
  put(KEY,sel.join(','));render()}}}});
q.oninput=render;render();
}})();
</script>"""
    with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(page(st["title"], body, st.get("subtitle", ""), extra_css=CSS,
                      head_extra=f'<meta property="og:title" content="{e(st["title"])}">'))
    print(f"OK – {len(posts)} ενημερώσεις στο /enimerwseis/")
