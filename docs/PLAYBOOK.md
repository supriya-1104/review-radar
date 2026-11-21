# Playbook: building Review Radar with Claude Code, day by day

Paste the prompts as they are, or put them in your own words. Read Claude's plan
before approving, and push back when something doesn't make sense to you.
That pushing back is the PM skill you're practising.

---

## Day 0: accounts (30 min)
1. Claude Pro or Max plan (for Claude Code).
2. Anthropic Console: API key, $5–10 credit, **monthly spend limit set**.
3. Apify: free account (includes monthly free credit); copy your API token.
   Set a spend limit there too.
4. Install Python 3.11+, Git, VS Code; have a GitHub account.

## Day 1: setup + PRD + first place (Claude Code: CLAUDE.md, plan mode)
1. Unzip this kit into a folder called `review-radar`.
2. Install Claude Code:
   - macOS/Linux: `curl -fsSL https://claude.ai/install.sh | bash`
   - Windows PowerShell: `irm https://claude.ai/install.ps1 | iex`
   - Check: `claude --version`
3. `cd review-radar`, run `claude`, sign in.
4. Rewrite `docs/PRD.md` in your own words first. Then:

> Read CLAUDE.md, docs/PRD.md and docs/PLAYBOOK.md. Summarise the product back to
> me in 5 bullets and list anything in the PRD that's unclear or risky.

> Set up the repo: Python virtual env, requirements.txt, folder structure from
> CLAUDE.md, .env from .env.example (I'll paste the keys myself). Initialise git
> and commit. Explain each step.

5. Create an empty public GitHub repo `review-radar`, then:

> Connect this repo to github.com/<your-username>/review-radar and push. Walk me
> through any login step.

6. Press **Shift+Tab** until plan mode is on, then:

> Read docs/specs/01-connect-place.md. Compare two Apify Google Maps reviews
> actors on price, exact dates, and reliability, then plan the ingest. Don't
> write code yet.

Approve, build, run it on your first place, commit. Fill Day 1 of `BUILD_LOG.md`
and decisions D1–D2.

## Day 2: aspect tagging (Claude Code: specific prompts, permissions, git)
Also today: message 5 restaurant owners to book interviews (docs/owner-interviews.md).
Read 50 reviews yourself and write your aspect list. Then:

> Read docs/specs/02-aspects.md. Here is my aspect list: <paste>. Plan it, then
> build after I approve. Estimate the cost before running on all reviews.

> Show me 20 random tagged reviews with their quotes so I can check them.

> Commit with a clear message.

## Day 3: dashboard (Claude Code: checkpoints and rewind)
> Read docs/specs/03-dashboard.md. Build src/metrics.py first with tests, then
> the Streamlit layout.

Try two versions of the "Fix this first" formula. Build version A, look at the
result for all 3 places, then use **rewind** (`/rewind`, or Esc twice) and try
version B:

> Compare A and B side by side for my 3 places. Which ranking matches what a
> human reading the reviews would say?

Pick one, record why in DECISIONS.md, commit.

## Day 4: AI analyst agent (Claude Code: plan mode for multi-file work)
> Read docs/specs/04-analyst-agent.md. Plan the tool loop and approval gate.
> Show me the tool descriptions before writing code.

> Explain how the agent loop works in plain words, as if I'm explaining it in
> an interview.

> Add the prompt-injection review and prove the agent doesn't follow it.

## Day 5: tracing + error analysis (Claude Code: MCP)
> Read docs/specs/05-tracing-error-analysis.md. Add Arize Phoenix tracing.

> Help me write 30 realistic owner questions across my 3 places in
> evals/questions.jsonl. Include 5 with no good answer.

Then **read every trace yourself** and fill `docs/error-analysis.md`. Optional
MCP practice: add the GitHub MCP server (ask Claude Code how) and have it open
issues for your top failure modes.

## Day 6: evals (Claude Code: skills)
> Read docs/specs/06-evals.md and evals/rubric.md. Build the eval runner.

Hand-label the 100 reviews and 30 answers yourself, then:

> Run all evals, report judge agreement, save the baseline.

> Create a Claude Code skill called run-evals that runs the suite and summarises
> what changed since the last report.

## Day 7: fix, polish, deploy (Claude Code: subagents, hooks)
> Read docs/specs/07-fix-deploy.md. My top 2 failure modes are <paste>. For each,
> suggest 2 fixes and what you'd expect to change in the evals.

> Create a code-reviewer subagent and have it check for leaked keys, prompt
> injection risks and cost risks before deploy.

> Add a hook that runs the code checks after every edit to src/.

Deploy to Streamlit Community Cloud with demo mode on. Test on your phone.

## Day 8: README, demo, real users
> Fill README.md from evals/results, DECISIONS.md and error-analysis.md. Add a
> Mermaid architecture diagram. Keep it skimmable in 2 minutes.

Record a 2–3 minute video: problem (20 s), paste a link → dashboard (60 s),
eval results + one failure you fixed (60 s), what's next (20 s).
Show it to 3 business owners; record what they said. Pin the repo.

---

### If you get stuck
- "I don't understand X. Explain it simply, then show me where it is in our code."
- Errors: paste the full error and ask "what does this mean and what are 2 ways
  to fix it?"
- Going in circles: `/clear`, then restart from the spec with a narrower ask.
