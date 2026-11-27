"""The non-dashboard screens: Ask analyst, Replies, All reviews (spec 03 §7, spec 04).

Approval gate: replies are saved ONLY by the Approve button in reply_box().
The analyst can draft and ask to save, never save.
"""

import hashlib
import html
import re
from datetime import date

import streamlit as st

from src import agent, db, metrics, replies, tools
from src.aspects import ASPECTS, PROBLEM_LABELS
from src.privacy import hide_names
from src.tag import clean_text

e = html.escape


def short_key(review_id: str) -> str:
    """Widget keys: Google review ids share long prefixes, so hash the whole id."""
    return hashlib.md5(review_id.encode()).hexdigest()[:10]


def _ctx(conn, place_id: str, place_name: str) -> tools.ToolContext:
    """A fresh ToolContext each rerun (SQLite connections can't cross threads),
    with refs and drafts kept in the session so [R3] means the same review."""
    mem = st.session_state.setdefault(f"ctx-{place_id}", {"refs": {}, "by_review": {}, "drafts": {}})
    ctx = tools.ToolContext(conn, place_id, place_name, metrics.today())
    ctx.refs, ctx.by_review, ctx.drafts = mem["refs"], mem["by_review"], mem["drafts"]
    return ctx


def review_card(conn, place_name: str, review_id: str, label: str = "") -> None:
    r = metrics.review_text(conn, review_id)
    if not r:
        return
    when = date.fromisoformat(r["published_at"][:10]).strftime("%d %b %Y")
    body = e(hide_names(clean_text(r["text_translated"] or r["text"]), place_name))
    st.markdown(f"<div class='rr-muted'>{e(label)} {'★' * r['stars']}{'☆' * (5 - r['stars'])} · {when}"
                f"{' · ✓ owner replied on Google' if r['owner_reply'] else ''}</div>"
                f"<div class='rr-review'>{body}</div>", unsafe_allow_html=True)


def reply_box(conn, place_id: str, place_name: str, review_id: str, key: str,
              suggested: str | None = None, source: str = "owner") -> None:
    """Draft -> edit -> Approve / Reject. The only place a reply is ever saved."""
    saved = replies.for_place(place_id).get(review_id)
    if saved:
        st.success(f"Saved reply (approved {saved['approved_at'][:10]}, not posted to Google):\n\n{saved['text']}")
        return
    state = st.session_state.setdefault(f"reply-{key}", {"text": suggested, "rejected": False})
    if state["rejected"]:
        st.caption("Draft rejected. Nothing was saved.")
        if st.button("Start again", key=f"{key}-again"):
            state.update(text=None, rejected=False)
            st.rerun()
        return
    if state["text"] is None:
        c1, c2 = st.columns([2, 1])
        tone = c2.selectbox("Tone", ["warm", "apologetic", "brief"], key=f"{key}-tone",
                            label_visibility="collapsed")
        if c1.button("✍ Draft a reply", key=f"{key}-draft", width="stretch"):
            with st.spinner("Drafting…"):
                ctx = _ctx(conn, place_id, place_name)
                out = tools.run_tool(ctx, "draft_reply", {"review": review_id, "tone": tone})
            state["text"] = out.get("draft") or f"(Couldn't draft: {out.get('error', 'no answer')})"
            st.rerun()
        return
    text = st.text_area("Reply draft: edit before approving", state["text"], key=f"{key}-text", height=130)
    for f in tools.check_reply(text):
        st.warning(f"⚠ {f}")
    a, b = st.columns(2)
    if a.button("✓ Approve & save", key=f"{key}-ok", type="primary", width="stretch"):
        replies.save_approved(place_id, review_id, text, source, tools.check_reply(text))
        st.rerun()
    if b.button("✕ Reject", key=f"{key}-no", width="stretch"):
        state["rejected"] = True
        st.rerun()
    st.caption("Saving keeps it in Review Radar only. Nothing is posted to Google.")


# ---------------- Ask analyst ----------------

EXAMPLES = [
    "Why did our rating change in the last 30 days?",
    "Is the weekend worse than weekdays for slow service?",
    "What do people say about the biryani?",
    "Draft replies to this month's 1-star reviews",
]


def _render_answer(conn, place_id: str, place_name: str, msg: dict, i: int) -> None:
    ans: agent.Answer = msg["answer"]
    text = agent.REF.sub(lambda m: f"**[{m.group(1)}]**", ans.text)
    st.markdown(text)
    if ans.unverified_numbers:
        st.warning(f"⚠ Not verified: {', '.join(ans.unverified_numbers)} didn't come from any tool result. "
                   "Treat with care.")
    if ans.bad_refs:
        st.warning(f"⚠ Cites {', '.join(ans.bad_refs)}, which no tool returned.")
    if ans.cited:
        with st.expander(f"Reviews cited ({len(ans.cited)})"):
            for ref, rid in ans.cited.items():
                review_card(conn, place_name, rid, f"[{ref}]")
    for d in ans.drafts:
        with st.expander(f"Reply draft for [{d['ref']}]", expanded=True):
            review_card(conn, place_name, d["review_id"], f"[{d['ref']}]")
            reply_box(conn, place_id, place_name, d["review_id"], f"ask{i}-{d['ref']}", d["draft"], "analyst")
    for p in ans.pending_saves:
        with st.expander(f"The analyst asked to save a reply to [{p['ref']}]: your approval needed",
                         expanded=True):
            review_card(conn, place_name, p["review_id"], f"[{p['ref']}]")
            reply_box(conn, place_id, place_name, p["review_id"], f"save{i}-{p['ref']}", p["text"], "analyst")
    with st.expander(f"How I got this: {len(ans.steps)} tool calls · {ans.seconds}s"):
        for s in ans.steps:
            st.markdown(f"**{s['step']}. {s['tool']}** `{tools.to_json(s['args'])}`")
        if ans.used_fallback:
            st.caption("The smart model was busy, so the fast model finished this answer.")


def ask_view(conn, place_id: str, place_name: str) -> None:
    st.markdown(f"<div class='rr-section'><h2>Ask the analyst</h2><div class='rr-sub'>Questions about "
                f"{e(place_name)}'s reviews. Answers use only your data and cite the reviews [R1].</div></div>",
                unsafe_allow_html=True)
    chat = st.session_state.setdefault(f"chat-{place_id}", {"messages": [], "history": []})
    if not chat["messages"]:
        st.caption("Try one:")
        for q in EXAMPLES:
            if st.button(q, key=f"ex-{q}", width="stretch"):
                st.session_state["pending_q"] = q
                st.rerun()
    for i, msg in enumerate(chat["messages"]):
        with st.chat_message(msg["role"], avatar="🧑‍🍳" if msg["role"] == "user" else "📡"):
            if msg["role"] == "user":
                st.markdown(msg["text"])
            else:
                _render_answer(conn, place_id, place_name, msg, i)
    q = st.chat_input("Ask about your reviews…") or st.session_state.pop("pending_q", None)
    if q:
        chat["messages"].append({"role": "user", "text": q})
        with st.status("Thinking: looking at your reviews…", expanded=False):
            ctx = _ctx(conn, place_id, place_name)
            ans, chat["history"] = agent.ask(q, ctx, chat["history"])
        chat["messages"].append({"role": "assistant", "answer": ans})
        st.rerun()
    if chat["messages"] and st.button("New conversation"):
        st.session_state.pop(f"chat-{place_id}")
        st.rerun()


# ---------------- Replies ----------------

def replies_view(conn, place_id: str, place_name: str) -> None:
    saved = replies.for_place(place_id)
    rows = conn.execute(
        "SELECT review_id FROM reviews WHERE place_id = ? AND stars <= 3 AND has_text = 1 "
        "AND (owner_reply IS NULL OR owner_reply = '') ORDER BY published_at DESC", (place_id,)).fetchall()
    todo = [r["review_id"] for r in rows if r["review_id"] not in saved]
    st.markdown(f"<div class='rr-section'><h2>Replies</h2><div class='rr-sub'>{len(todo)} bad reviews "
                f"(1–3★) with no reply on Google yet, newest first · {len(saved)} replies approved. "
                f"Every reply needs your approval; nothing is posted to Google.</div></div>",
                unsafe_allow_html=True)
    tab_todo, tab_saved = st.tabs([f"Need a reply ({len(todo)})", f"Approved ({len(saved)})"])
    with tab_todo:
        for rid in todo[:10]:
            review_card(conn, place_name, rid)
            reply_box(conn, place_id, place_name, rid, f"rep-{short_key(rid)}")
            st.divider()
        if len(todo) > 10:
            st.caption(f"Showing the newest 10 of {len(todo)}.")
    with tab_saved:
        if not saved:
            st.caption("No approved replies yet.")
        for rid, r in saved.items():
            review_card(conn, place_name, rid)
            st.success(f"{r['text']}\n\n_Approved {r['approved_at'][:10]} · from {r['source']} · "
                       f"not posted to Google_")


# ---------------- All reviews ----------------

def reviews_view(conn, place_id: str, place_name: str) -> None:
    st.markdown("<div class='rr-section'><h2>All reviews</h2><div class='rr-sub'>Every review with text, "
                "newest first. Filter by stars or topic.</div></div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    stars = c1.multiselect("Stars", [1, 2, 3, 4, 5], default=[], placeholder="All stars")
    topic = c2.selectbox("Complaint about", ["Any"] + list(ASPECTS),
                         format_func=lambda k: k if k == "Any" else PROBLEM_LABELS[k])
    sql = "SELECT DISTINCT r.review_id FROM reviews r"
    args: list = []
    if topic != "Any":
        sql += " JOIN aspects a ON a.review_id = r.review_id AND a.aspect = ? AND a.sentiment = 'neg'"
        args.append(topic)
    sql += " WHERE r.place_id = ? AND r.has_text = 1"
    args.append(place_id)
    if stars:
        sql += f" AND r.stars IN ({','.join('?' for _ in stars)})"
        args += stars
    ids = [r[0] for r in conn.execute(sql + " ORDER BY r.published_at DESC", args).fetchall()]
    st.caption(f"{len(ids)} reviews match · showing up to 30")
    for rid in ids[:30]:
        review_card(conn, place_name, rid)
