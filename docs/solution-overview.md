# Solution Overview

## What We Built

DocuVerity is a guided examination workflow that runs inside IBM Bob. An examiner describes what they observed on a suspected forged document, and Bob — calling out to a small MCP server we built — turns those observations into a classified anomaly type, a confidence score, a set of relevant examination standards, and a drafted expert opinion report. The examiner stays in control at every step: DocuVerity structures and accelerates their reasoning, it doesn't replace their judgment.

## How It Works

1. The examiner tells Bob what they observed, in conversation (e.g. "the signature stroke pattern doesn't match the exemplar, and the paper fluoresces differently under UV").
2. Bob normalizes this into a structured observation record and calls the `classify_anomaly` MCP tool, which returns the anomaly category (e.g. Signature Forgery, Typographic Forgery, Physical Substrate Tampering, Digital Metadata Tampering, or Composite).
3. Bob calls `score_forgery_confidence`, which applies a weighted rubric across the flagged indicators and returns a 0–100 confidence score plus a breakdown of which indicators drove it.
4. Bob calls `map_to_examination_standard`, which links the anomaly category to the relevant questioned-document examination standard references.
5. Bob calls `draft_expert_report`, which compiles all of the above into a structured, section-by-section expert opinion report the examiner can review, edit, and export.

## Architecture Diagram

> See [`architecture.md`](architecture.md) for the detailed diagram.

```
[Examiner] → [IBM Bob] → [DocuVerity MCP Server]
                              ├─ classify_anomaly
                              ├─ score_forgery_confidence
                              ├─ map_to_examination_standard
                              └─ draft_expert_report → [Report Markdown]
                                          ↑
                              (optional) watsonx.ai — report language polish
```

## Key Design Decisions

| Decision | Rationale |
|---|---|
| Four separate MCP tools instead of one "do everything" tool | Keeps Bob's reasoning inspectable at each stage — judges and examiners can see exactly which stage produced which finding, instead of one opaque black box |
| Rule-based, documented scoring instead of a trained ML classifier | No labeled forged-document dataset was available in the hackathon timeframe; a transparent rubric is more defensible for a report that may face cross-examination than an unexplainable model score |
| watsonx.ai used only for optional language polishing of the final report, not for the forensic judgment itself | Keeps the actual classification/scoring logic auditable and reproducible, while still giving a genuine, real use for watsonx.ai |
| Stateless per-session design | Matches the hackathon scope — each examination is self-contained; a persistence layer is a documented known limitation, not a hidden gap |

## IBM Technologies Used

- **IBM Bob:** Bob is the conversational front-end and orchestrator — it collects the examiner's free-form description, decides which MCP tool to call and in what order, and presents the results back conversationally. This is the primary, load-bearing integration.
- **watsonx.ai (optional):** When configured, the `draft_expert_report` tool sends the compiled findings to a watsonx.ai foundation model to smooth the report's language into formal expert-opinion prose; without an API key configured, the tool falls back to a clean template-based render so the demo works offline.
