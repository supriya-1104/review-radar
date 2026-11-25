"""Review Radar dashboard (spec 03). Run: streamlit run src/app.py

One scrolling phone-width page: header -> summary card -> sticky tabs ->
Fix first -> What's working -> Rating trend -> All complaints -> bottom bar.
Every number comes from src/metrics.py; the summary sentence from
src/summary.py (grounding-checked). Review text is always HTML-escaped.
"""

import html
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # so `src.` imports work

import plotly.graph_objects as go
import streamlit as st

from src import db, metrics, summary
from src.privacy import hide_names
from src.tag import clean_text

st.set_page_config(page_title="Review Radar", page_icon="📡", layout="centered")

TEAL, CORAL, YELLOW, LAVENDER, PEACH, INK, CREAM = (
    "#2F7F6E", "#EE7B8E", "#F6B73C", "#B3A8F2", "#F7CBA4", "#1F1D1B", "#FBF3E4")

e = html.escape  # every piece of review text goes through this


def stars(x) -> str:
    return f"{x:.1f}★" if x is not None else "–"


# ---------------- styles ----------------

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
html, body, .stApp, .stApp p, .stApp div, .stApp label, button, input {{ font-family: 'Plus Jakarta Sans', sans-serif !important; }}
[data-testid="stIconMaterial"], .material-symbols-rounded {{ font-family: 'Material Symbols Rounded' !important; }}
div[data-testid="stHorizontalBlock"] {{ flex-wrap: nowrap !important; gap: 8px !important; }}
div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {{ min-width: 0 !important; width: auto !important; flex: 1 1 0 !important; }}
iframe[height="1"] {{ display: none; }}
header[data-testid="stHeader"], #MainMenu, footer {{ display: none !important; }}
.stApp {{ background: {CREAM}; }}
.block-container {{ max-width: 430px !important; padding: 14px 14px 110px !important; }}
h1, h2, h3, p {{ color: {INK}; }}
.rr-muted {{ color: #6E655B; font-size: 13px; }}
.rr-card {{ border-radius: 26px; padding: 18px 18px 16px; margin: 0 0 12px; position: relative; overflow: hidden; }}
.rr-summary {{ background: {TEAL}; color: #fff; }}
.rr-summary * {{ color: #fff; }}
.rr-summary .rr-curve {{ position: absolute; right: -40px; top: -40px; width: 170px; height: 170px;
  border: 26px solid rgba(255,255,255,.12); border-radius: 50%; }}
.rr-eyebrow {{ font-size: 11px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; opacity: .85; }}
.rr-big {{ font-size: 52px; font-weight: 800; line-height: 1; margin: 6px 0 2px; }}
.rr-tiles {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: 14px 0 12px; }}
.rr-tile {{ background: rgba(255,255,255,.14); border-radius: 16px; padding: 10px 11px; font-size: 12.5px; line-height: 1.35; }}
.rr-tile b {{ font-size: 16px; }}
.rr-next {{ background: {YELLOW}; border-radius: 18px; padding: 12px 14px; margin-top: 10px; }}
.rr-next, .rr-next * {{ color: {INK} !important; }}
.rr-next a {{ font-weight: 700; text-decoration: none; }}
.rr-low {{ display: inline-block; border: 1.5px dashed currentColor; border-radius: 999px; padding: 1px 8px;
  font-size: 11px; font-weight: 700; margin-left: 6px; }}
.rr-tabs {{ display: flex; gap: 4px; background: {CREAM}; padding: 8px 0 8px; }}
.rr-tabs a {{ flex: 1; text-align: center; padding: 10px 2px; border-radius: 999px; font-size: 12px; white-space: nowrap; font-weight: 700;
  color: {INK} !important; text-decoration: none !important; background: #F1E3CB; min-height: 20px; }}
.rr-tabs a.active {{ background: {INK}; color: #fff !important; }}
div[data-testid="stElementContainer"]:has(.rr-tabs) {{ position: sticky; top: 0; z-index: 50; background: {CREAM}; }}
.rr-section {{ scroll-margin-top: 64px; margin: 22px 0 4px; }}
.rr-section h2 {{ font-size: 22px; font-weight: 800; margin: 0; padding: 0; }}
.rr-sub {{ color: #6E655B; font-size: 13px; margin: 2px 0 10px; }}
.rr-note {{ background: #F1E3CB; border-radius: 14px; padding: 8px 12px; font-size: 12.5px; margin-bottom: 10px; }}
.rr-row {{ display: flex; align-items: center; gap: 12px; border-radius: 20px; padding: 12px 14px; margin-bottom: 8px; background: #fff; }}
.rr-row.sel {{ background: {CORAL}; }}
.rr-rank {{ font-size: 13px; font-weight: 800; width: 26px; }}
.rr-row .t {{ flex: 1; font-size: 13px; line-height: 1.35; }}
.rr-row .t b {{ font-size: 15px; }}
.rr-ring {{ width: 46px; height: 46px; border-radius: 50%; display: grid; place-items: center; flex: none; }}
.rr-ring span {{ width: 34px; height: 34px; border-radius: 50%; background: #fff; display: grid; place-items: center;
  font-size: 11px; font-weight: 800; color: {INK}; }}
.rr-why {{ background: {INK}; color: #fff; }}
.rr-why * {{ color: #fff; }}
.rr-why ol {{ padding-left: 18px; margin: 8px 0 0; font-size: 13.5px; line-height: 1.45; }}
.rr-review {{ background: #fff; border-radius: 20px; padding: 14px; font-size: 14px; line-height: 1.45; margin: 4px 0 8px; }}
.rr-review mark {{ background: {PEACH}; border-radius: 6px; padding: 0 3px; }}
.rr-strength {{ border-radius: 22px; padding: 14px 16px; margin-bottom: 8px; }}
.rr-strength .n {{ font-size: 13px; font-weight: 700; }}
.rr-strength .q {{ font-size: 13.5px; margin-top: 6px; font-style: italic; }}
.rr-bar {{ display: grid; grid-template-columns: 1fr auto; gap: 4px 10px; align-items: center; margin-bottom: 11px; font-size: 13px; }}
.rr-bar .track {{ grid-column: 1 / 3; height: 14px; background: #F1E3CB; border-radius: 999px; overflow: hidden; }}
.rr-bar .fill {{ height: 100%; border-radius: 999px; }}
.rr-badge {{ font-size: 11.5px; font-weight: 700; border-radius: 999px; padding: 2px 8px; white-space: nowrap; }}
.rr-nav {{ position: fixed; bottom: 0; left: 50%; transform: translateX(-50%); width: min(430px, 100%);
  background: {INK}; border-radius: 22px 22px 0 0; display: flex; justify-content: space-around; padding: 8px 6px 12px; z-index: 100; }}
.rr-nav a {{ color: #fff !important; text-decoration: none !important; font-size: 11px; font-weight: 600; text-align: center;
  min-width: 70px; min-height: 44px; opacity: .65; position: relative; }}
.rr-nav a.on {{ opacity: 1; }}
.rr-nav a .i {{ display: block; font-size: 19px; line-height: 1.3; }}
.rr-nav a .dot {{ position: absolute; top: -2px; right: 12px; background: {CORAL}; color: {INK}; border-radius: 999px;
  font-size: 10px; font-weight: 800; padding: 0 5px; }}
div[data-testid="stSelectbox"] label, div[data-testid="stSegmentedControl"] label {{ font-size: 12px !important; }}
</style>
""", unsafe_allow_html=True)


# ---------------- data ----------------

conn = db.connect()
places = conn.execute("SELECT place_id, name FROM places ORDER BY name").fetchall()
if not places:
    st.title("Review Radar")
    st.info('No places yet. Run `python -m src.ingest "<Google Maps link>"` then `python -m src.tag --all`.')
    st.stop()


@st.cache_data(show_spinner="Writing the summary…")
def cached_summary(place_id: str, place_name: str, as_of: date) -> dict:
    c = db.connect()
    s = metrics.summary(c, place_id, as_of)
    w = metrics.choose_window(c, place_id, as_of)
    return summary.write_summary(place_name, s, w, metrics.priorities(c, place_id, w),
                                 metrics.strengths(c, place_id, w))


# ---------------- 0 · header ----------------

names = {p["place_id"]: p["name"] for p in places}
default = next((p["place_id"] for p in places if p["name"].startswith("Meghana")), places[0]["place_id"])
top_l, top_r = st.columns([2.4, 1], vertical_alignment="bottom")
with top_l:
    place_id = st.selectbox("Restaurant ▾", list(names), index=list(names).index(default),
                            format_func=lambda k: names[k], key="place")
with top_r:
    with st.popover("+ Add", width="stretch", help="Add a place: paste a Google Maps link"):
        link = st.text_input("Paste a Google Maps link", placeholder="https://maps.app.goo.gl/…")
        st.caption("Pulls the newest 500 reviews (about $0.30 on Apify) and tags them with Gemini. Takes 2–5 minutes.")
        if st.button("Analyse this place", disabled=not link):
            from src import ingest, tag
            with st.status("Analysing…", expanded=True) as status:
                st.write("Fetching reviews…")
                st.code(ingest.ingest(link), language=None)
                c = db.connect()
                new_id = c.execute("SELECT place_id FROM places WHERE source_input = ?", (link,)).fetchone()[0]
                st.write("Tagging what each review is about…")
                tag.tag_place(c, new_id, names.get(new_id, "new place"))
                status.update(label="Done", state="complete")
            st.session_state["place"] = new_id
            st.rerun()

place = metrics.place_header(conn, place_id)
as_of = metrics.today()
s = metrics.summary(conn, place_id, as_of)
w = metrics.choose_window(conn, place_id, as_of)
top = metrics.priorities(conn, place_id, w)
strong = metrics.strengths(conn, place_id, w)
comps = metrics.complaints(conn, place_id, w)
trend = metrics.monthly_trend(conn, place_id, as_of)
text = cached_summary(place_id, place["name"], as_of)

st.markdown(
    f"<div class='rr-muted'>{e(place.get('category') or '')} · All-time Google rating "
    f"<b>{stars(place.get('total_score'))}</b> · {place.get('reviews_count', 0):,} reviews on Google</div>",
    unsafe_allow_html=True)


# ---------------- 1 · summary card ----------------

last, prev = s.last, s.prev
low = (f"<span class='rr-low'>low confidence: only {last['n']} reviews</span>"
       if last["n"] < metrics.LOW_CONFIDENCE else "")
if s.change is None:
    change = "no reviews to compare"
elif s.change < 0:
    change = f"▼ down {abs(s.change):.1f} stars"
elif s.change > 0:
    change = f"▲ up {s.change:.1f} stars"
else:
    change = "■ same"
share = f"{100 * s.bad_share:.0f}%" if s.bad_share is not None else "–"
if s.normal_bad_share is None:
    usual = "no earlier reviews to compare"
elif s.normal_n < metrics.LOW_CONFIDENCE:
    usual = f"too few earlier reviews to compare ({s.normal_n})"
else:
    usual = f"a normal month {100 * s.normal_bad_share:.0f}% ({s.normal_n} reviews)"
arrow = ""
if s.bad_share is not None and s.normal_bad_share is not None and s.normal_n >= metrics.LOW_CONFIDENCE:
    arrow = "▲ " if s.bad_share > s.normal_bad_share else ("▼ " if s.bad_share < s.normal_bad_share else "■ ")

st.markdown(f"""
<div class="rr-card rr-summary"><div class="rr-curve"></div>
  <div class="rr-eyebrow">Last 30 days · {metrics.fmt_range(last['start'], last['end'])}</div>
  <div class="rr-big">{stars(last['avg'])}</div>
  <div>average from <b>{last['n']}</b> new reviews{low}</div>
  <div class="rr-tiles">
    <div class="rr-tile">Previous 30 days<br><b>{stars(prev['avg'])}</b> · {prev['n']} reviews<br>{change}</div>
    <div class="rr-tile">Bad reviews (1–3★)<br><b>{last['bad']} of {last['n']}</b> · {share}<br>{arrow}{usual}</div>
  </div>
  <div style="font-size:15px;line-height:1.45">{e(text['headline'])}</div>
  <div class="rr-next"><div class="rr-eyebrow" style="opacity:1">Do this next</div>
    <div style="font-size:14.5px;font-weight:600;margin:3px 0 6px">{e(text['do_next'])}</div>
    <a href="#rr-fix">See the reviews behind it →</a></div>
</div>""", unsafe_allow_html=True)
if text["source"] == "template":
    st.caption("Summary uses a plain template: the AI's version failed a fact check.")


# ---------------- 2 · sticky tabs ----------------

st.markdown("""<div class="rr-tabs" id="rr-tabs">
<a href="#rr-fix" data-t="rr-fix" class="active">Fix first</a><a href="#rr-working" data-t="rr-working">Working</a>
<a href="#rr-trend" data-t="rr-trend">Trend</a><a href="#rr-complaints" data-t="rr-complaints">Complaints</a></div>""",
            unsafe_allow_html=True)

window_note = (f"<div class='rr-note'>📅 {e(w.label)} ({w.range_text}). {e(w.reason)}</div>"
               if w.widened else "")


def section(anchor: str, title: str, subtitle: str) -> None:
    st.markdown(f"<div class='rr-section' id='{anchor}'><h2>{title}</h2>"
                f"<div class='rr-sub'>{subtitle}</div></div>", unsafe_allow_html=True)


# ---------------- 3 · Fix first ----------------

total_complaints = metrics.complaint_review_count(conn, place_id, w)
section("rr-fix", "1 · Fix first",
        f"The problems that cost you the most stars · {w.label.lower()} ({w.range_text})")
st.markdown(window_note, unsafe_allow_html=True)

if not top:
    st.markdown("<div class='rr-note'>Not enough complaints to rank problems yet "
                f"(each needs at least {metrics.MIN_FIX_MENTIONS}).</div>", unsafe_allow_html=True)
else:
    shown = top[:3]
    pick = st.segmented_control("See why", [f"#{i + 1}" for i in range(len(shown))], default="#1",
                                key=f"pick-{place_id}") or "#1"
    sel = int(pick[1:]) - 1
    rows = ""
    for i, p in enumerate(shown):
        pct = round(100 * p.n / total_complaints) if total_complaints else 0
        ring = f"conic-gradient({INK if i == sel else CORAL} {pct * 3.6}deg, #F1E3CB 0)"
        normal = ""
        if p.normal is not None:
            unit = "month" if w.days == 30 else w.label.lower().replace("last ", "")
            normal = f" · a normal {unit}: {p.normal:g}"
        rows += (f"<div class='rr-row {'sel' if i == sel else ''}'><div class='rr-rank'>#{i + 1}</div>"
                 f"<div class='t'><b>{e(p.label)}</b><br>In {p.n} of {total_complaints} reviews with "
                 f"complaints ({p.n_bad_reviews} of them 1–3★) · cost {p.stars_lost:g} stars{normal}</div>"
                 f"<div class='rr-ring' style='background:{ring}'><span>{pct}%</span></div></div>")
    st.markdown(rows, unsafe_allow_html=True)

    p = shown[sel]
    avg_these = sum(m["stars"] for m in p.evidence) / len(p.evidence)
    rose = ""
    if p.normal is not None:
        diff = p.n - p.normal
        rose = (f" A normal {'month' if w.days == 30 else w.label.lower().replace('last ', '')} has {p.normal:g}, "
                f"so this is {'up' if diff > 0 else 'down' if diff < 0 else 'the same'}"
                + (f" by {abs(diff):g}." if diff else "."))
    st.markdown(f"""<div class="rr-card rr-why"><div class="rr-eyebrow">Why #{sel + 1} is on this list</div>
<ol><li>It comes up in <b>{p.n}</b> reviews ({w.label.lower()}), <b>{p.n_bad_reviews}</b> of them 1–3★.</li>
<li>Those reviews average <b>{avg_these:.1f}★</b>, against <b>{stars(p.drag + avg_these)}</b> for all reviews in the same period.</li>
<li>Together they cost you <b>{p.stars_lost:g} stars</b> (each review's missing stars, shared between the problems it mentions).{rose}</li></ol></div>""",
                unsafe_allow_html=True)

    key = f"rev-{place_id}-{p.aspect}"
    idx = st.session_state.get(key, 0) % len(p.evidence)
    m = p.evidence[idx]
    r = metrics.review_text(conn, m["review_id"])
    body = e(hide_names(clean_text(r["text_translated"] or r["text"]), place["name"]))
    q = e(hide_names(m["quote"], place["name"]))
    body = body.replace(q, f"<mark>{q}</mark>", 1) if q in body else body
    when = date.fromisoformat(r["published_at"][:10]).strftime("%d %b %Y")
    reply = "✓ owner replied" if r["owner_reply"] else "no reply yet"
    st.markdown(f"<div class='rr-muted'>Review {idx + 1} of {len(p.evidence)} · {'★' * r['stars']}"
                f"{'☆' * (5 - r['stars'])} · {when} · {reply}</div>"
                f"<div class='rr-review'>{body}</div>", unsafe_allow_html=True)
    b1, b2, b3 = st.columns([1, 1, 2.2])
    if b1.button("◀", key=f"{key}-p", width="stretch"):
        st.session_state[key] = idx - 1
        st.rerun()
    if b2.button("▶", key=f"{key}-n", width="stretch"):
        st.session_state[key] = idx + 1
        st.rerun()
    b3.button("✍ Draft reply (Day 4)", key=f"{key}-d", disabled=True, width="stretch",
              help="Reply drafts come with the AI analyst. Saving or posting always needs your approval.")


# ---------------- 4 · What's working ----------------

section("rr-working", "2 · What's working",
        f"What the {strong['good_with_text']} good reviews (4–5★) with text praise · "
        f"{w.label.lower()} ({w.range_text})")
colours = [TEAL, LAVENDER, PEACH]
if not strong["items"]:
    st.markdown("<div class='rr-note'>No praise tagged in this period.</div>", unsafe_allow_html=True)
for i, it in enumerate(strong["items"]):
    fg = "#fff" if colours[i] == TEAL else INK
    st.markdown(f"""<div class="rr-strength" style="background:{colours[i]};color:{fg}">
<div style="font-size:17px;font-weight:800">{e(it['label'])}</div>
<div class="n">{it['n']} of {strong['good_with_text']} good reviews ({100 * it['share']:.0f}%)</div>
<div class="q">“{e(hide_names(it['quote']['quote'], place['name']))}”</div></div>""", unsafe_allow_html=True)


# ---------------- 5 · Rating trend ----------------

section("rr-trend", "3 · Rating trend", "Average stars per calendar month · tap a dot for details")
data_start = conn.execute("SELECT MIN(published_at) FROM reviews WHERE place_id = ?", (place_id,)).fetchone()[0]
loaded_from = data_start[:7] if data_start else None

xs, ys, hover, conf, sizes = [], [], [], [], []
prev_pt = None
for t in trend:
    if t["avg"] is None:
        continue
    month = date(t["year"], int(t["month"][5:]), 1)
    period = (f"{month:%B} (1–{t['through_day']} {month:%b}, so far)" if t["partial"]
              else f"{month:%B %Y}")
    msg = f"{period}: {t['avg']:.1f}★ from {t['n']} reviews."
    if prev_pt:
        d = t["avg"] - prev_pt["avg"]
        msg += (f"<br>{'Down' if d < 0 else 'Up' if d > 0 else 'Same as'} {abs(d):.1f}★ "
                f"{'from' if d else ''} {prev_pt['label']} ({prev_pt['avg']:.1f}★).").replace("Same as 0.0★ ", "Same as ")
    if t["low_confidence"]:
        msg += f"<br>Low confidence: fewer than {metrics.LOW_CONFIDENCE} reviews, one review moves it a lot."
    xs.append(t["month"]); ys.append(t["avg"]); hover.append(msg); conf.append(not t["low_confidence"])
    prev_pt = t

ticks = [t["month"] for t in trend]
tick_text = [f"{t['label']}<br>{t['year']}" if (i == 0 or t["label"] == "Jan") else t["label"]
             for i, t in enumerate(trend)]
fig = go.Figure()
fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=INK, width=2.5, shape="spline"),
                         hoverinfo="skip", showlegend=False))
fig.add_trace(go.Scatter(
    x=xs, y=ys, mode="markers", showlegend=False, text=hover, hovertemplate="%{text}<extra></extra>",
    marker=dict(size=[13 if c else 12 for c in conf],
                color=[TEAL if c else CREAM for c in conf],
                symbol=["circle" if c else "circle-open-dot" for c in conf],
                line=dict(width=2.5, color=[TEAL if c else CORAL for c in conf]))))
fig.update_layout(
    height=260, margin=dict(l=6, r=6, t=10, b=6), paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)", font=dict(family="Plus Jakarta Sans", color=INK, size=12),
    hoverlabel=dict(bgcolor=INK, font_color="#fff", font_size=12, bordercolor=INK),
    xaxis=dict(tickmode="array", tickvals=ticks, ticktext=tick_text, range=[-0.5, len(ticks) - 0.5],
               type="category", categoryorder="array", categoryarray=ticks, showgrid=False, fixedrange=True,
               tickangle=0, tickfont=dict(size=10)),
    yaxis=dict(title="Average stars", range=[1, 5.2], dtick=1, ticksuffix="★", gridcolor="#EADBC2",
               fixedrange=True))
st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
notes = [f"● filled = {metrics.LOW_CONFIDENCE}+ reviews that month · ◎ hollow = fewer (low confidence)"]
if loaded_from and loaded_from > ticks[0]:
    lf = date.fromisoformat(loaded_from + "-01")
    notes.append(f"Reviews before {lf:%b %Y} aren't loaded (we pull the newest 500), so earlier months are blank.")
st.markdown("<div class='rr-muted'>" + "<br>".join(notes) + "</div>", unsafe_allow_html=True)


# ---------------- 6 · All complaints ----------------

section("rr-complaints", "4 · All complaints",
        f"What {total_complaints} reviews with complaints mention, and how that compares with normal")
st.markdown(window_note, unsafe_allow_html=True)
if w.days == 30:
    opt_now, opt_normal = f"This month ({w.range_text})", "A normal month"
else:
    opt_now, opt_normal = f"{w.label} ({w.range_text})", f"A normal {w.label.lower().replace('last ', '')}"
view = st.segmented_control("Show", [opt_now, opt_normal], default=opt_now, key=f"view-{place_id}") or opt_now

if not comps:
    st.markdown("<div class='rr-note'>No complaints in this period.</div>", unsafe_allow_html=True)
elif view == opt_normal and w.baseline_start is None:
    st.markdown("<div class='rr-note'>Not enough earlier reviews to say what normal looks like.</div>",
                unsafe_allow_html=True)
else:
    show_now = view == opt_now
    vals = [(c, c["n"] if show_now else (c["normal"] or 0)) for c in comps]
    vals = [v for v in vals if v[1] > 0]
    vals.sort(key=lambda v: -v[1])
    biggest = max(v for _, v in vals) if vals else 1
    bars = ""
    for c, v in vals:
        badge = ""
        if show_now and c["delta"] is not None:
            d = c["delta"]
            if d >= 0.5:
                badge = f"<span class='rr-badge' style='background:{CORAL}'>↑ {d:g} more</span>"
            elif d <= -0.5:
                badge = f"<span class='rr-badge' style='background:#CDE7DF'>↓ {abs(d):g} fewer</span>"
            else:
                badge = "<span class='rr-badge' style='background:#F1E3CB'>■ same</span>"
        colour = CORAL if show_now else LAVENDER
        from_bad = f" ({c['n_bad_reviews']} in 1–3★)" if show_now else " a period on average"
        bars += (f"<div class='rr-bar'><div><b>{e(c['label'])}</b> · {v:g}{from_bad}</div>"
                 f"<div>{badge}</div><div class='track'><div class='fill' style='width:{100 * v / biggest:.0f}%;"
                 f"background:{colour}'></div></div></div>")
    st.markdown(bars, unsafe_allow_html=True)
foot = f"This period: {w.range_text}."
if w.baseline_start:
    unit = "month" if w.days == 30 else w.label.lower().replace("last ", "")
    foot += f" A normal {unit}: average of {w.baseline_text} ({w.baseline_periods:.1f} × {w.days} days)."
st.markdown(f"<div class='rr-muted'>{foot} Counts are complaints; one review can complain about several things.</div>",
            unsafe_allow_html=True)


# ---------------- 7 · bottom bar ----------------

badge = metrics.unreplied_bad(conn, place_id)
st.markdown(f"""<div class="rr-nav">
<a class="on" href="#"><span class="i">▦</span>Dashboard</a>
<a title="Coming soon: every review, filterable"><span class="i">☰</span>All reviews</a>
<a title="Coming on Day 4"><span class="i" style="color:{YELLOW}">✦</span>Ask analyst</a>
<a title="Coming on Day 4: drafts waiting for your approval"><span class="i">✉</span>Replies<span class="dot">{badge}</span></a>
</div>""", unsafe_allow_html=True)

# Scroll-spy: highlight the tab of the section on screen (runs in the parent page).
st.iframe("""<script>
const doc = window.parent.document;
function spy() {
  const tabs = doc.querySelectorAll('#rr-tabs a');
  if (!tabs.length) return;
  let current = tabs[0].dataset.t;
  for (const a of tabs) {
    const sec = doc.getElementById(a.dataset.t);
    if (sec && sec.getBoundingClientRect().top < 140) current = a.dataset.t;
  }
  tabs.forEach(a => a.classList.toggle('active', a.dataset.t === current));
}
if (!window.parent.__rrSpy) { doc.addEventListener('scroll', spy, true); window.parent.__rrSpy = true; }
spy();
</script>""", height=1)
