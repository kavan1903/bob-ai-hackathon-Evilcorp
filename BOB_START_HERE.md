# Start Here — Kickoff Instructions for IBM Bob

> Human teammate: tell Bob to read this file first thing tomorrow morning.
> Bob: read this whole file before touching any code. It gives you the
> context you need — team, chosen problem, current repo state, and what
> to actually do today.

## 1. Event & Team

- **Event:** IBM Bob AI Hackathon x NFSU
- **Team:** Evilcorp — lead Kavan Hada, members Aryan Sagar & Dhruvang Upadhyay
- **Track:** AI (Forensic Science track in the original NFSU problem list, mapped to "AI" for the submission template's required track field)
- **Deadline logistics:** submission is a public GitHub repo; `submission.yaml` is read by evaluators first, then the README, then the actual code in `src/`.

## 2. Which problem statement, and why

Of the 12 NFSU problem statements, we picked **#01 — AI-Powered Document Forgery Detection Assistant**, built as a project called **DocuVerity**. Reasoning (in case scope questions come up mid-hackathon):
- Clean, structured input→output pipeline that's realistic to finish in a hackathon
- No sensitive-data/ethics concerns (unlike the child-safety or trafficking problem statements), so demo video/screenshots are safe to publish
- Directly aligned with NFSU's own specialty (forensic document examination), which should read well to judges
- The 4-stage design (classify → score → map-to-standard → draft-report) gives Bob distinct, inspectable tool calls instead of one opaque prompt — this is deliberately built to score well on the "IBM Bob Integration" rubric criterion (10 pts), not just the "Technical Implementation" one (25 pts)

Read the full framing in `docs/problem-statement.md` and `docs/solution-overview.md` before changing direction on scope.

## 3. What already exists — read these files first, in this order

1. `submission.yaml` — the structured source of truth: title, problem statement, solution summary, key features, tech stack, known limitations. Keep this in sync with whatever you actually build.
2. `docs/solution-overview.md` — the intended mechanism: examiner reports observations → `classify_anomaly` → `score_forgery_confidence` → `map_to_examination_standard` → `draft_expert_report`.
3. `docs/architecture.md` — component diagram and data flow.
4. `src/mcp_server/forensics.py` — the actual classification/scoring/report logic. Currently **rule-based heuristics**, not a trained model (see `known_limitations` in `submission.yaml` for why, and keep that disclosure honest and up to date as you change things).
5. `src/mcp_server/server.py` — wraps `forensics.py` as 4 MCP tools; also has a `--demo` mode you can run directly (`python server.py --demo`) without any Bob/MCP wiring, to sanity-check the pipeline.
6. `src/mcp_server/watsonx_polish.py` — optional watsonx.ai call to polish the final report's language; safely no-ops if `WATSONX_API_KEY` isn't set, so don't let this block anything.
7. `.bob/mcp.json` — already wires this server into you (Bob) as the `docuverity` MCP server. If your tools panel doesn't show `docuverity`, see the "Connecting to IBM Bob" section in `docs/setup-guide.md` for the manual fallback.

Run `python server.py --demo` from `src/mcp_server/` right now, before doing anything else, to confirm your baseline actually works on this machine.

## 4. What to actually do today — in priority order

Judging weights (100 pts total): Technical Implementation 25, Innovation 25, Problem Depth 15, Working Demo 15, Bob Integration 10, Docs 10. Spend effort accordingly — a genuinely working, well-reasoned pipeline beats a half-finished bigger one.

1. **Verify the baseline** (above), then verify the same flow works *through you as Bob* — e.g. ask yourself/get asked: "I have a suspected forged property document — signature stroke pattern doesn't match the exemplar, and the paper fluoresces differently under UV. Classify this and draft a report." Confirm you call `classify_anomaly_tool` → `score_forgery_confidence_tool` → `map_to_examination_standard_tool` → `draft_expert_report_tool` in sequence and the report comes back sensible.
2. **Deepen `forensics.py`** — the current scoring/classification is a first-pass heuristic (see `INDICATOR_WEIGHTS`, `ANOMALY_CATEGORY_MAP`, `EXAMINATION_STANDARDS` in that file). Improve it: more indicator nuance, better-justified weights, more anomaly categories, more realistic standard mappings. This is where most of the "Technical Implementation" and "Innovation" points come from — don't just leave it as-is.
3. **Get real test material** — see the dataset recommendations already discussed for this project (CEDAR signature database for genuine/forged signature pairs, MIDV-2020/FMIDV for forged identity documents). Use a real genuine/forged pair to drive an actual example through the pipeline for the demo, instead of only synthetic text descriptions.
4. **Keep `known_limitations` honest** — if you add real scoring logic, update the limitations text; don't let the docs overclaim relative to what the code does (judges explicitly penalize that).
5. **Once something real runs end-to-end:** take ≥3 screenshots into `demo/screenshots/`, record a 3–5 min demo video and put the link in `demo/demo-video-link.txt` (currently still a placeholder — the GitHub Action will fail until this is replaced), and build `presentation/slides.pdf`.
6. **Don't touch:** `.github/workflows/validate.yml`, `CONTRIBUTING.md`, the top-level file/folder structure (rules from the submission template — see `docs/template-guide.md` if you need the reasoning).

## 5. Constraints to respect while you work

- No sensitive/real victim data — everything stays mock/synthetic or from public research datasets (see above).
- Don't fabricate ML/AI capability claims in docs that the code doesn't actually do — this repo's whole design intentionally favors transparent, inspectable logic over unverifiable claims.
- Standards referenced in `EXAMINATION_STANDARDS` (`forensics.py`) are illustrative placeholders, not verified legal citations — flag this if you expand it, don't present it as authoritative.
