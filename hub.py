"""Dark 'Strategy Analytics Hub' theme - a separate visual language from report.py's light
'Backtest Studio' theme, used only on the Strategy Hub page. Number formatting (inr/num/dt/...)
is reused from report.py; only the markup/CSS here is dark-theme specific."""
import html

import report as R

BG, PANEL, PANEL2 = "#0B1120", "#121A2E", "#0E1526"
BORDER = "rgba(255,255,255,.08)"
TEXT, MUTED, MUTED2 = "#E7ECF5", "#8893AD", "#5E6B85"
POS, NEG, ACCENT, ACCENT2, WARN = "#22D3A0", "#FB5B5B", "#4C8DFF", "#22C3E6", "#F5B544"

CSS = f"""<style>
/* Strategy Hub: full dark re-skin, scoped to pages with a .sh root so other pages are untouched */
.sh {{ font-family:"Segoe UI",Inter,Arial,Helvetica,sans-serif; color:{TEXT} }}
.sh *{{ box-sizing:border-box }}
/* The sidebar is shared app chrome - it must look identical on every page (report.py's light
   theme), never recoloured by whichever page happens to be open, so only the main content
   area (.stApp's background, behind the sidebar) and this page's own widgets go dark. */
body:has(.sh) .stApp {{ background:{BG} !important }}
body:has(.sh) [data-testid=stHeader] {{ background:transparent !important }}
body:has(.sh) [data-testid=stFileUploader] section {{ background:{PANEL2} !important; border:1.5px dashed rgba(76,141,255,.45) !important }}
body:has(.sh) [data-testid=stFileUploader] section:hover {{ border-color:{ACCENT} !important; background:#0F1830 !important }}
body:has(.sh) [data-testid=stFileUploader] small, body:has(.sh) [data-testid=stFileUploaderFileName] {{ color:{MUTED} !important }}
body:has(.sh) [data-testid=stWidgetLabel] p {{ color:{MUTED} !important }}
body:has(.sh) input, body:has(.sh) [data-baseweb=input] {{ background:{PANEL2} !important; color:{TEXT} !important; border-color:{BORDER} !important }}
body:has(.sh) [data-testid=stBaseButton-primary] {{ background:{ACCENT} !important }}
body:has(.sh) [data-testid=stBaseButton-secondary] {{ background:{PANEL2} !important; color:{TEXT} !important; border-color:{BORDER} !important }}
body:has(.sh) [data-testid=stDataFrame] {{ border:1px solid {BORDER} !important; border-radius:10px !important }}
body:has(.sh) [data-testid=stExpander] {{ background:{PANEL} !important; border:1px solid {BORDER} !important; border-radius:12px !important }}
body:has(.sh) [data-testid=stVerticalBlockBorderWrapper] {{ background:{PANEL} !important; border:1px solid {BORDER} !important; box-shadow:none !important }}
body:has(.sh) [data-testid=stCheckbox] label p, body:has(.sh) [data-testid=stWidgetLabel] label p {{ color:{MUTED} !important }}
body:has(.sh) [data-baseweb=select] > div {{ background:{PANEL2} !important; color:{TEXT} !important; border-color:{BORDER} !important }}
body:has(.sh) [data-baseweb=popover] li {{ background:{PANEL} !important; color:{TEXT} !important }}
body:has(.sh) [data-testid=stTabs] [role=tab] {{ color:{MUTED} !important }}
body:has(.sh) [data-testid=stTabs] [aria-selected=true] {{ color:{TEXT} !important }}

.sh .eyebrow{{ color:{ACCENT}; font:700 10px/1 Arial; letter-spacing:.16em; margin:0 0 6px }}
.sh h1{{ color:{TEXT}; font-size:26px; font-weight:800; margin:0 0 6px }}
.sh .deck{{ color:{MUTED}; font-size:13.5px; margin:0 0 4px; max-width:760px }}
.sh h2{{ color:{TEXT}; font-size:15px; font-weight:700; margin:28px 0 12px; display:flex; align-items:center; gap:8px }}
.sh h2 i{{ width:4px; height:16px; border-radius:2px; background:{ACCENT}; display:inline-block }}

.sh .kpis{{ display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:12px; margin:8px 0 18px }}
.sh .kpi{{ background:{PANEL}; border:1px solid {BORDER}; border-top:3px solid var(--c,{ACCENT}); border-radius:12px; padding:16px 16px 14px }}
.sh .kpi .l{{ font-size:10px; letter-spacing:.07em; text-transform:uppercase; color:{MUTED2}; font-weight:700; margin-bottom:8px }}
.sh .kpi .v{{ font-size:22px; font-weight:800; line-height:1.1; color:{TEXT} }}
.sh .kpi .v.pos{{ color:{POS} }} .sh .kpi .v.neg{{ color:{NEG} }}
.sh .kpi .s{{ font-size:11px; color:{MUTED}; margin-top:6px }}
@media(max-width:1100px){{ .sh .kpis{{ grid-template-columns:repeat(2,1fr) }} }}

.sh .filebar{{ display:flex; flex-wrap:wrap; gap:8px; margin:10px 0 16px }}
.sh .chip{{ display:flex; align-items:center; gap:8px; background:{PANEL}; border:1px solid {BORDER}; border-radius:10px; padding:8px 12px; font-size:12px }}
.sh .chip b{{ color:{TEXT} }}
.sh .chip .tag{{ font-size:9.5px; font-weight:800; letter-spacing:.04em; padding:2px 7px; border-radius:20px }}
.sh .chip .tag.algo{{ background:rgba(76,141,255,.16); color:{ACCENT} }}
.sh .chip .tag.sm{{ background:rgba(34,195,230,.16); color:{ACCENT2} }}
.sh .chip .tag.pr{{ background:rgba(245,181,68,.16); color:{WARN} }}
.sh .chip .n{{ color:{MUTED} }}
.sh .chip.err{{ border-color:rgba(251,91,91,.45) }}

.sh .panel{{ background:{PANEL}; border:1px solid {BORDER}; border-radius:14px; padding:18px 20px; margin-bottom:16px }}
.sh .note{{ font-size:11.5px; color:{MUTED}; line-height:1.6; margin:0 0 10px }}
.sh .ok{{ background:rgba(34,211,160,.1); border:1px solid rgba(34,211,160,.3); color:{POS}; border-radius:9px; padding:9px 13px; font-size:12px; margin:8px 0 }}
.sh .warn{{ background:rgba(245,181,68,.1); border:1px solid rgba(245,181,68,.35); color:{WARN}; border-radius:9px; padding:9px 13px; font-size:12px; margin:8px 0 }}
.sh .bad{{ background:rgba(251,91,91,.1); border:1px solid rgba(251,91,91,.35); color:{NEG}; border-radius:9px; padding:9px 13px; font-size:12px; margin:8px 0 }}

.sh table{{ width:100%; border-collapse:collapse; font-size:12.5px }}
.sh thead th{{ text-align:right; font-size:10px; letter-spacing:.06em; text-transform:uppercase; color:{MUTED2}; font-weight:700; padding:10px 10px; border-bottom:1px solid {BORDER} }}
.sh thead th:first-child{{ text-align:left }}
.sh tbody td{{ text-align:right; padding:10px 10px; border-bottom:1px solid {BORDER}; color:{TEXT} }}
.sh tbody td:first-child{{ text-align:left; color:{MUTED}; font-weight:600 }}
.sh tbody tr:last-child td{{ border-bottom:0 }}
.sh td.good{{ color:{POS}; font-weight:700 }} .sh td.bad{{ color:{NEG}; font-weight:700 }}
.sh td.hl{{ color:{ACCENT} }} .sh td.mid{{ color:{MUTED}; text-align:center }}
.sh .badge{{ display:inline-block; font-size:10.5px; font-weight:800; padding:2px 7px; border-radius:5px; margin-left:5px; vertical-align:1px }}
.sh .badge.pe{{ background:rgba(76,141,255,.16); color:{ACCENT} }}
.sh .badge.ce{{ background:rgba(34,211,160,.16); color:{POS} }}

.sh .heat{{ font-size:11.5px }}
.sh .heat thead th{{ text-align:center }}
.sh .heat td{{ text-align:center; font-weight:700; padding:10px 6px }}
.sh .heat td.yr{{ text-align:left; color:{TEXT}; font-weight:800 }}
.sh .heat td.nil{{ color:{MUTED2}; font-weight:400 }}
.sh .heat tr.tot td{{ border-top:2px solid {BORDER}; font-weight:800 }}

.sh .empty{{ max-width:620px; margin:7vh auto; text-align:center; background:{PANEL}; border:1px solid {BORDER}; border-radius:16px; padding:36px 32px }}
.sh .empty b{{ display:block; font-size:19px; color:{TEXT}; margin-bottom:10px }}
.sh .empty .steps{{ text-align:left; display:inline-block; margin-top:12px; font-size:13px; line-height:1.9; color:{MUTED} }}
.sh .cap{{ font-size:11px; color:{MUTED2}; line-height:1.5; margin:4px 0 0 }}
</style>"""

PLOTLY_DARK = dict(template="plotly_dark", plot_bgcolor=PANEL2, paper_bgcolor="rgba(0,0,0,0)",
                   font=dict(family="Segoe UI, Arial", size=12, color=MUTED),
                   margin=dict(l=10, r=10, t=48, b=10),
                   legend=dict(orientation="h", y=1.12, x=1, xanchor="right", font=dict(color=TEXT)),
                   xaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER), yaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER))


def wrap(inner):
    return f'<div class="sh">{inner}</div>'


def hero(title, deck):
    return (f'<div class="eyebrow">STRATEGY ANALYTICS HUB</div><h1>{html.escape(title)}</h1>'
           f'<p class="deck">{deck}</p>')


def h2(title):
    return f'<h2><i></i>{html.escape(title)}</h2>'


def kpis(items):
    """items: (label, value, sub, tone, color) tone in '', 'pos', 'neg'; color sets the top accent bar."""
    return '<div class="kpis">' + "".join(
        f'<div class="kpi" style="--c:{c}"><div class="l">{l}</div><div class="v {t}">{v}</div><div class="s">{s}</div></div>'
        for l, v, s, t, c in items) + "</div>"


def chip(name, kind, n, warn=None, err=None):
    tag = {"StockMock": "sm", "Previous report": "pr"}.get(kind, "algo")
    label = kind if kind in ("StockMock", "Previous report") else "AlgoTest"
    cls = " err" if err else ""
    body = f'<span class="tag {tag}">{label}</span><b>{html.escape(name)}</b><span class="n">{n} trades</span>'
    if err:
        body = f'<span class="tag" style="background:rgba(251,91,91,.18);color:{NEG}">ERROR</span><b>{html.escape(name)}</b>'
    return f'<div class="chip{cls}">{body}</div>'


def table(headers, rows, cls=""):
    def cell(c):
        return f'<td class="{c[1]}">{c[0]}</td>' if isinstance(c, tuple) else f"<td>{c}</td>"
    return (f'<table class="{cls}"><thead><tr>' + "".join(f"<th>{h}</th>" for h in headers) + "</tr></thead><tbody>"
            + "".join("<tr>" + "".join(cell(c) for c in r) + "</tr>" for r in rows) + "</tbody></table>")


def type_badge(t):
    t = str(t or "").strip().upper()
    if t == "PE":
        return '<span class="badge pe">PE</span>'
    if t == "CE":
        return '<span class="badge ce">CE</span>'
    return ""


def heatmap(mat, yearly):
    """Dark year x month heatmap: text coloured by sign, no background fill (matches the dark reference)."""
    import pandas as pd
    mo = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    ys = yearly.set_index("Year")
    body = ""
    for y, r in mat.iterrows():
        cells = "".join(f'<td class="{R.sgn(v)}">{R.ind(v) if not pd.isna(v) else ""}</td>' if not pd.isna(v)
                        else '<td class="nil">–</td>' for v in r)
        tot, ret = ys.loc[y, "Net P&L"], ys.loc[y].get("Return %")
        body += (f'<tr><td class="yr">{y}</td>{cells}<td class="{R.sgn(tot)}">{R.ind(tot)}</td>'
                + (f'<td class="hl">{ret:.1f}%</td>' if ret is not None and not pd.isna(ret) else '<td class="mid">–</td>')
                + "</tr>")
    colt = mat.sum(min_count=1)
    grand = ys["Net P&L"].sum()
    gret = ys.get("Return %")
    gret_s = f'{gret.sum():.1f}%' if gret is not None else "–"
    tot_cells = "".join(f'<td class="{R.sgn(v)}">{R.ind(v)}</td>' if not pd.isna(v) else '<td class="nil">–</td>'
                        for v in colt)
    body += f'<tr class="tot"><td class="yr">All</td>{tot_cells}<td class="{R.sgn(grand)}">{R.ind(grand)}</td><td class="hl">{gret_s}</td></tr>'
    return (f'<table class="heat"><thead><tr><th style="text-align:left">Year</th>'
           + "".join(f"<th>{m}</th>" for m in mo) + '<th>Total</th><th>Return</th></tr></thead><tbody>'
           + body + "</tbody></table>")
