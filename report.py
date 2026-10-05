"""HTML building blocks for the professional report look (style reference: Backtest Report Studio).
Pure string builders - no Streamlit calls - so they are easy to test and reuse."""
import html
import re

import pandas as pd

NAVY, NAVY2, POS, NEG = "#1F4E79", "#16324F", "#1E7B45", "#B3261E"
LONG, SHORT, COMB = "#1F4E79", "#D9822B", "#16324F"

CSS = f"""<style>
.rp{{font-family:Arial,Helvetica,sans-serif;color:#1A1A1A;font-variant-numeric:tabular-nums}}
.rp *{{box-sizing:border-box}}
.rp .eyebrow{{color:{NAVY};font:700 10px/1 Arial;letter-spacing:.16em;margin:0 0 8px}}
.rp h1{{font:700 26px/1.2 Arial;margin:0 0 4px;color:#14324f}}
.rp .deck{{color:#5A6675;font-size:13px;margin:0 0 14px}}
.rp h2{{font:700 16px/1.3 Arial;margin:30px 0 0;color:#14324f}}
.rp h2 .n{{display:inline-block;background:{NAVY};color:#fff;border-radius:4px;padding:1px 8px;margin-right:8px;font-size:13px}}
.rp .hr{{height:2.5px;background:{NAVY};margin:6px 0 14px}}
.rp h3{{font:700 13px/1.3 Arial;margin:18px 0 4px;color:#25313f}}
.rp p{{font-size:13px;line-height:1.6;margin:0 0 10px}}
.rp .meta{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:0 24px;background:#F2F5F8;
  border-left:3px solid {NAVY};padding:10px 16px;font-size:12.5px;margin-bottom:10px}}
.rp .meta div{{padding:3px 0}}
.rp .kpis{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:10px 0 14px}}
.rp .kpi{{border:1px solid #D5DAE0;background:#fff;border-radius:8px;padding:14px 16px;min-height:92px;border-top:3px solid {NAVY}}}
.rp .kpi .l{{font-size:10px;text-transform:uppercase;letter-spacing:.06em;color:#6C7885;font-weight:700;margin-bottom:6px}}
.rp .kpi .v{{font-size:23px;font-weight:800;color:#14324f;line-height:1.1}}
.rp .kpi .v.pos{{color:{POS}}} .rp .kpi .v.neg{{color:{NEG}}}
.rp .kpi .s{{font-size:10.5px;color:#718090;margin-top:5px}}
.rp .cards{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:10px 0 16px}}
.rp .card{{border:1px solid #D5DAE0;border-radius:9px;background:#fff;padding:14px 16px}}
.rp .card h4{{margin:0 0 10px;font-size:13px;color:#14324f;display:flex;align-items:center;gap:7px}}
.rp .card h4 i{{width:10px;height:10px;border-radius:2px;display:inline-block}}
.rp .grid3{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}}
.rp .it{{background:#F6F8FA;border-radius:6px;padding:7px 9px}}
.rp .it .l{{font-size:9px;color:#728091;text-transform:uppercase;font-weight:700}}
.rp .it .v{{font-size:13px;font-weight:800;color:#25313f;margin-top:2px}}
.rp table{{width:100%;border-collapse:collapse;font-size:12.5px;margin:10px 0 6px;background:#fff}}
.rp thead th{{background:{NAVY};color:#fff;font-weight:700;text-align:right;padding:9px 10px;border:1px solid {NAVY};font-size:11.5px;line-height:1.3}}
.rp thead th:first-child{{text-align:left}}
.rp tbody td{{border:1px solid #D5DAE0;padding:8px 10px;text-align:right;line-height:1.4;color:#1A1A1A}}
.rp tbody td:first-child{{text-align:left;font-weight:700;color:#25313f}}
.rp tbody tr:nth-child(even){{background:#F7F9FB}}
.rp td.good{{color:{POS};font-weight:700;background:#EAF5EF}}
.rp td.bad{{color:{NEG};font-weight:700;background:#FBECEA}}
.rp td.hl{{color:{NAVY};font-weight:700;background:#EEF3F9}}
.rp td.mid{{text-align:center;color:#5A6675;font-size:11px;font-weight:400}}
.rp .tag{{display:inline-block;font-size:9px;color:#fff;background:{NAVY2};padding:1px 6px;border-radius:2px;margin-left:6px;font-weight:400}}
.rp .pc{{color:#5A6675;font-weight:400;font-size:11px;white-space:nowrap}}
.rp .heat{{table-layout:fixed;font-size:11px}}
.rp .heat thead th{{text-align:center;padding:7px 2px;font-size:11px}}
.rp .heat td{{padding:9px 2px;border:1px solid #fff;text-align:center;font-weight:700;color:#1A1A1A}}
.rp .heat td:first-child{{background:{NAVY2};color:#fff;text-align:center}}
.rp .heat td.nil{{background:#FAFBFC;color:#CBD2DA;font-weight:400}}
.rp .heat tr.tot td{{border-top:2px solid {NAVY2}}}
.rp .scale{{display:flex;align-items:center;gap:8px;font-size:10.5px;color:#5A6675;margin:6px 0 12px}}
.rp .scale .bar{{flex:0 0 160px;height:8px;background:linear-gradient(90deg,{NEG},#EBC9C6 42%,#F4F6F8 50%,#C8E2D3 58%,{POS})}}
.rp .cap{{font-size:11px;line-height:1.5;color:#5A6675;margin:2px 0 14px}}
.rp .callout{{border-left:3px solid {NAVY};background:#EEF3F9;padding:11px 14px;font-size:12.5px;margin:12px 0;line-height:1.55}}
.rp .ok{{border:1px solid #B8D9C5;background:#F0F8F3;color:#245B38;border-radius:7px;padding:9px 12px;font-size:12px;margin:8px 0}}
.rp .warn{{border:1px solid #E6C36A;background:#FFF9E8;color:#654E16;border-radius:7px;padding:9px 12px;font-size:12px;margin:8px 0}}
.rp.guide td,.rp.guide th{{text-align:left!important}}
.rp .empty{{max-width:640px;margin:5vh auto;text-align:center;color:#5A6675;background:#fff;border:1px solid #D9E0E8;border-radius:14px;padding:34px 30px;box-shadow:0 1px 3px rgba(20,50,79,.06)}}
.rp .empty b{{display:block;font-size:20px;color:#14324f;margin-bottom:10px}}
.rp .steps{{text-align:left;display:inline-block;margin-top:10px;font-size:13px;line-height:1.9}}
@media(max-width:900px){{.rp .kpis{{grid-template-columns:repeat(2,1fr)}}.rp .cards{{grid-template-columns:1fr}}}}
@media print{{[data-testid=stSidebar],[data-testid=stHeader],header,[data-testid=stToolbar]{{display:none!important}}
  .rp h2{{break-after:avoid}} .rp table,.rp .card,.rp .callout{{break-inside:avoid}}}}

/* ===== global app skin ===== */
.stApp{{background:linear-gradient(180deg,#EEF2F7 0,#F6F8FB 220px)}}
[data-testid=stHeader]{{background:transparent}}
[data-testid=stAppDeployButton],[data-testid=stMainMenu],#MainMenu,footer{{display:none!important}}
.block-container{{padding-top:1.6rem;max-width:1320px}}
[data-testid=stSidebar]{{background:#fff;border-right:1px solid #E1E6EC}}
[data-testid=stSidebar] h3{{font-size:13px;letter-spacing:.08em;text-transform:uppercase;color:#1F4E79;margin-top:.4rem}}
/* ===== smooth page switching ===== */
[data-stale="true"]{{opacity:1!important;transition:none!important}}
[data-testid=stStatusWidget]{{visibility:hidden}}
[data-testid=stMain] .block-container{{animation:rpfade .28s ease-out}}
@keyframes rpfade{{from{{opacity:0;transform:translateY(6px)}}to{{opacity:1;transform:none}}}}
[data-testid=stSidebarNavLink],[data-testid=stBaseButton-primary],[data-testid=stBaseButton-secondary]{{transition:background .15s,color .15s}}
@media (prefers-reduced-motion:reduce){{[data-testid=stMain] .block-container{{animation:none}}}}
/* ===== sidebar navigation ===== */
[data-testid=stSidebar] > div:first-child{{padding-top:0}}
[data-testid=stSidebarHeader]{{padding:14px 16px 0}}
[data-testid=stSidebarNav]{{padding:0 12px 8px}}
[data-testid=stSidebarNav]::before{{content:"BACKTEST STUDIO";display:block;font:800 15px/1.1 "Segoe UI",Arial,sans-serif;letter-spacing:.14em;color:#16324F;
  padding:6px 10px 0}}
[data-testid=stSidebarNav]::after{{content:"";display:none}}
[data-testid=stSidebarNavItems]{{gap:4px;padding-top:46px;position:relative}}
[data-testid=stSidebarNavItems]::before{{content:"WORKFLOW";position:absolute;top:22px;left:10px;font:700 10.5px/1 "Segoe UI",Arial,sans-serif;
  letter-spacing:.14em;color:#8A97A6}}
[data-testid=stSidebarNavLink]{{border-radius:10px;padding:9px 12px;border-left:3px solid transparent;color:#3C4956;font-weight:600;transition:all .15s}}
[data-testid=stSidebarNavLink]:hover{{background:#F0F4F9;color:#1F4E79}}
[data-testid=stSidebarNavLink][aria-current=page]{{background:#E8EFF7;color:#16324F;border-left-color:#1F4E79;font-weight:700}}
[data-testid=stSidebarNavLink] span[data-testid=stIconMaterial]{{color:#1F4E79;font-size:20px}}
[data-testid=stSidebarNavSeparator]{{display:none}}
[data-testid=stFileUploader] section{{border:1.6px dashed #8FA9C4;background:#fff;border-radius:12px;padding:18px}}
[data-testid=stFileUploader] section:hover{{border-color:#1F4E79;background:#F7FAFD}}
[data-testid=stBaseButton-primary],[data-testid=stBaseButton-primary] *{{color:#fff!important}}
[data-testid=stBaseButton-primary]{{background:#1F4E79;border:0;border-radius:8px;font-weight:700;padding:.5rem 1.1rem}}
[data-testid=stBaseButton-primary]:hover{{background:#16324F}}
[data-testid=stBaseButton-secondary]{{border-radius:8px;border:1px solid #C9D3DF;font-weight:600}}
[data-testid=stVerticalBlockBorderWrapper]{{background:#fff;border-radius:12px;border:1px solid #D9E0E8;box-shadow:0 1px 2px rgba(20,50,79,.05)}}
[data-testid=stTabs] [role=tab]{{font-weight:700}}
[data-testid=stDataFrame]{{border:1px solid #D9E0E8;border-radius:8px;overflow:hidden}}

/* ===== stepper / hero / pills ===== */
.rp .hero{{background:linear-gradient(120deg,#16324F 0,#1F4E79 100%);color:#fff;border-radius:14px;padding:26px 30px;margin-bottom:16px}}
.rp .hero .eyebrow{{color:#9CC0E6}}
.rp .hero h1{{color:#fff;font-size:28px;margin:0 0 6px}}
.rp .hero p{{color:#D5E3F2;font-size:14px;margin:0;max-width:760px}}
.rp .stepper{{display:flex;gap:10px;margin:16px 0 0}}
.rp .stepper .st{{flex:1;display:flex;align-items:center;gap:10px;background:rgba(255,255,255,.10);border:1px solid rgba(255,255,255,.18);
  border-radius:10px;padding:10px 12px;color:#C5D6E9;font-size:12px}}
.rp .stepper .st b{{display:block;color:#fff;font-size:13px}}
.rp .stepper .st i{{font-style:normal;flex:0 0 28px;height:28px;border-radius:50%;background:rgba(255,255,255,.16);display:flex;align-items:center;justify-content:center;font-weight:800;color:#fff}}
.rp .stepper .st.on{{background:#fff;border-color:#fff;color:#4A5B6D}}
.rp .stepper .st.on b{{color:#16324F}} .rp .stepper .st.on i{{background:#1F4E79;color:#fff}}
.rp .stepper .st.done i{{background:#1E7B45}}
.rp .feat{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}}
.rp .feat div{{background:#F6F8FA;border-radius:8px;padding:10px 12px;font-size:12.5px;line-height:1.45}}
.rp .feat b{{display:block;color:#14324f;font-size:13px;margin-bottom:2px}}
.rp .banner{{display:flex;align-items:center;gap:12px;border-radius:10px;padding:12px 16px;font-size:13px;margin:6px 0 14px}}
.rp .banner.ok{{background:#EAF6EF;border:1px solid #BFE0CC;color:#1F5E3A}}
.rp .banner.bad{{background:#FDEDEB;border:1px solid #F0C1BC;color:#8A1F18}}
.rp .banner.next{{background:#EEF3F9;border:1px solid #CFDCEB;color:#16324F}}
.rp .dl-head{{display:flex;justify-content:space-between;align-items:center;margin-bottom:2px}}
.rp .dl-head h4{{margin:0;font-size:15px;color:#14324f;display:flex;align-items:center;gap:8px}}
.rp .dl-head i{{width:11px;height:11px;border-radius:3px;display:inline-block}}
.rp .dl-head span{{font-size:12px;color:#5A6675}}
</style>"""


# ---------- number formatting ----------
def ind(x):
    """Indian digit grouping, no decimals: 1234567 -> 12,34,567"""
    n = str(int(round(abs(x))))
    if len(n) > 3:
        n = re.sub(r"(\d)(?=(\d\d)+$)", r"\1,", n[:-3]) + "," + n[-3:]
    return n


def inr(x):
    return "n/a" if x is None or pd.isna(x) else ("-" if round(x) < 0 else "") + "₹" + ind(x)


def num(x, d=2, suf=""):
    return "n/a" if x is None or pd.isna(x) else f"{x:,.{d}f}{suf}"


def dur(m):
    return "n/a" if m is None or pd.isna(m) else (f"{m/60:.1f} h" if m >= 120 else f"{m:.0f} min")


def dt(x):
    return "n/a" if x is None or pd.isna(x) else pd.Timestamp(x).strftime("%d %b %Y")


def sgn(x):
    return "" if x is None or pd.isna(x) else "good" if x > 0 else "bad" if x < 0 else ""


def pct_of(v, base):
    """' (12.34%)' of user-supplied capital/margin; empty when not supplied."""
    return f' <span class="pc">({v / base * 100:.2f}%)</span>' if base and v is not None and not pd.isna(v) else ""


# ---------- blocks ----------
def wrap(inner, extra=""):
    return f'<div class="rp {extra}">{inner}</div>'


def h2(n, title):
    badge = f'<span class="n">{n}</span>' if n else ""
    return f'<h2>{badge}{html.escape(title)}</h2><div class="hr"></div>'


def kpis(items):
    """items: (label, value, sub, tone) tone in '', 'pos', 'neg'"""
    return '<div class="kpis">' + "".join(
        f'<div class="kpi"><div class="l">{l}</div><div class="v {t}">{v}</div><div class="s">{s}</div></div>'
        for l, v, s, t in items) + "</div>"


def cards(items):
    """items: (title, color, [(label, value), ...])"""
    return '<div class="cards">' + "".join(
        f'<div class="card"><h4><i style="background:{c}"></i>{html.escape(t)}</h4><div class="grid3">'
        + "".join(f'<div class="it"><div class="l">{l}</div><div class="v">{v}</div></div>' for l, v in kv)
        + "</div></div>" for t, c, kv in items) + "</div>"


def table(headers, rows, cls=""):
    """rows: lists of cells; a cell is 'text' or ('text', 'css-class'). Text is trusted HTML."""
    def cell(c):
        return f'<td class="{c[1]}">{c[0]}</td>' if isinstance(c, tuple) else f"<td>{c}</td>"
    return (f'<table class="{cls}"><thead><tr>' + "".join(f"<th>{h}</th>" for h in headers) + "</tr></thead><tbody>"
            + "".join("<tr>" + "".join(cell(c) for c in r) + "</tr>" for r in rows) + "</tbody></table>")


def heatmap(mat, yearly, total_mdd, base):
    """mat: year x month (NaN = no trades); yearly: frame from core.monthly_matrix."""
    mo = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    vals = mat.stack().dropna().abs().sort_values()
    cap = vals.iloc[int(len(vals) * .9)] if len(vals) else 1  # clamp at 90th percentile like the reference
    cap = cap or 1

    def bg(v):
        a = min(1, abs(v) / cap) * .5 + .06
        return f"rgba(30,123,69,{a:.3f})" if v > 0 else f"rgba(179,38,30,{a:.3f})" if v < 0 else "#F4F6F8"

    def cell(v, extra=""):
        return (f'<td class="nil">–</td>' if pd.isna(v) else f'<td style="background:{bg(v)}" {extra}>{ind(v) if round(v) >= 0 else "-" + ind(v)}</td>')
    ys = yearly.set_index("Year")
    body = ""
    for y, r in mat.iterrows():
        tot = ys.loc[y, "Net P&L"]
        body += (f"<tr><td>{y}</td>" + "".join(cell(v) for v in r) + cell(tot)
                 + f'<td style="background:rgba(179,38,30,.10);color:{NEG}">{ind(ys.loc[y, "Max Drawdown"])}</td>'
                 + (f'<td class="hl">{tot / base * 100:.2f}%</td>' if base else "<td>–</td>") + "</tr>")
    colt = mat.sum(min_count=1)
    grand = ys["Net P&L"].sum()
    body += ('<tr class="tot"><td>All</td>' + "".join(cell(v) for v in colt) + cell(grand)
             + f'<td style="background:rgba(179,38,30,.10);color:{NEG}">{ind(total_mdd)}</td>'
             + (f'<td class="hl">{grand / base * 100:.2f}%</td>' if base else "<td>–</td>") + "</tr>")
    return (f'<table class="heat"><thead><tr><th>Year</th>' + "".join(f"<th>{m}</th>" for m in mo)
            + f"<th>Total</th><th>Max DD</th><th>ROI</th></tr></thead><tbody>{body}</tbody></table>"
            f'<div class="scale"><span>{inr(-cap)}</span><span class="bar"></span><span>{inr(cap)}</span>'
            '<span style="margin-left:auto">₹ by exit month. Shading is clamped at the 90th-percentile month; '
            "– = no trades. Year Max DD is within that year.</span></div>")


def hero(eyebrow, title, deck, active=None):
    """Dark hero banner; `active` 1-3 draws the stage tracker."""
    steps = [("Split signals", "TradingView → Long / Short files"), ("Backtest on AlgoTest", "Done on AlgoTest, outside this app"),
             ("Analyse report", "Upload both results")]
    trk = ""
    if active:
        trk = '<div class="stepper">' + "".join(
            f'<div class="st {"on" if i == active else "done" if i < active else ""}"><i>{"✓" if i < active else i}</i>'
            f'<span><b>{t}</b>{d}</span></div>' for i, (t, d) in enumerate(steps, 1)) + "</div>"
    return f'<div class="hero"><div class="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{deck}</p>{trk}</div>'
