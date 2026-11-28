"""Run the 30 owner questions through the analyst, traced in Phoenix (spec 05).

Run: python -m evals.run_questions        (start Phoenix first to see traces)

Resumable: answers are saved one by one to evals/results/runs-<date>.jsonl,
so if the free tier stops us, re-running continues where it left off.
Writes a readable report (evals/results/runs-<date>.md) to read next to the
traces while filling in docs/error-analysis.md. Both files contain review
quotes, so they stay local (gitignored).
"""

import json
import sys
from datetime import datetime
from pathlib import Path

from src import agent, db, metrics, tools, tracing

HERE = Path(__file__).resolve().parent
QUESTIONS = HERE / "questions.jsonl"
RESULTS = HERE / "results"


def load_questions() -> list[dict]:
    return [json.loads(line) for line in QUESTIONS.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    traced = tracing.setup()
    print("Tracing to Phoenix: http://localhost:6006" if traced else "Phoenix not running: no traces.")
    RESULTS.mkdir(exist_ok=True)
    qs = load_questions()
    # Continue the newest unfinished run (e.g. one cut off by a lost connection).
    out_path = RESULTS / f"runs-{datetime.now():%Y-%m-%d}.jsonl"
    for old in sorted(RESULTS.glob("runs-*.jsonl"), reverse=True):
        if len(old.read_text(encoding="utf-8").splitlines()) < len(qs):
            out_path = old
            print(f"Continuing {old.name}")
        break
    done = set()
    if out_path.exists():
        done = {json.loads(l)["id"] for l in out_path.read_text(encoding="utf-8").splitlines() if l.strip()}

    conn = db.connect()
    for q in qs:
        if q["id"] in done:
            continue
        pid, name = conn.execute("SELECT place_id, name FROM places WHERE name LIKE ?",
                                 (f"%{q['place']}%",)).fetchone()
        ctx = tools.ToolContext(conn, pid, name, metrics.today())
        try:
            ans, _ = agent.ask(q["question"], ctx)
        except Exception as e:  # e.g. daily free-tier limit: stop, resume later
            print(f"\nStopped at {q['id']}: {type(e).__name__}: {str(e)[:200]}\nRe-run to continue.")
            break
        rec = {**q, "place_name": name, "answer": ans.text,
               "steps": [{"tool": s["tool"], "args": s["args"], "result": s["result"]} for s in ans.steps],
               "cited": ans.cited, "unverified_numbers": ans.unverified_numbers, "bad_refs": ans.bad_refs,
               "drafts": [{"ref": d["ref"], "draft": d["draft"], "flags": d["flags"]} for d in ans.drafts],
               "pending_saves": len(ans.pending_saves), "hit_step_limit": ans.hit_step_limit,
               "seconds": ans.seconds, "tokens": ans.tokens}
        with out_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
        flags = []
        if ans.unverified_numbers:
            flags.append(f"unverified {ans.unverified_numbers}")
        if ans.bad_refs:
            flags.append(f"bad refs {ans.bad_refs}")
        print(f"{q['id']} {q['place']:<10} {len(ans.steps)} calls {ans.seconds:>5}s  {'; '.join(flags)}")

    write_report(out_path, out_path.with_suffix(".md"))
    return 0


def write_report(jsonl: Path, md: Path) -> None:
    recs = [json.loads(l) for l in jsonl.read_text(encoding="utf-8").splitlines() if l.strip()]
    lines = [f"# Analyst runs: {jsonl.stem[5:]}", "",
             f"{len(recs)} questions. Read each one (and its trace in Phoenix) and fill "
             "docs/error-analysis.md.", ""]
    for r in recs:
        lines += [f"## {r['id']} · {r['place_name']} · {r['type']}", "",
                  f"**Q:** {r['question']}", "", f"**A good answer:** {r['good_answer']}", "",
                  "**Tool calls:**", ""]
        lines += [f"{i}. `{s['tool']}({json.dumps(s['args'], ensure_ascii=False)})`"
                  for i, s in enumerate(r["steps"], 1)] or ["(none)"]
        lines += ["", "**Answer:**", "", "> " + r["answer"].replace("\n", "\n> "), ""]
        auto = []
        if r["unverified_numbers"]:
            auto.append(f"numbers not in any tool result: {r['unverified_numbers']}")
        if r["bad_refs"]:
            auto.append(f"cited reviews no tool returned: {r['bad_refs']}")
        if r["hit_step_limit"]:
            auto.append("hit the 8-call limit")
        for d in r["drafts"]:
            if d["flags"]:
                auto.append(f"draft [{d['ref']}] flagged: {d['flags']}")
        lines += [f"**Automatic checks:** {'; '.join(auto) if auto else 'none raised'} · "
                  f"{len(r['steps'])} tool calls · {r['seconds']}s", "", "---", ""]
    md.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReport: {md}")


if __name__ == "__main__":
    raise SystemExit(main())
