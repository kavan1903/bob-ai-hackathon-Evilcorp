# 🚀 DocuVerity — AI Forgery Examination Assistant

## 👥 Team

| Field | Value |
|---|---|
| **Team Name** | Evilcorp |
| **Track** | AI |
| **Team Lead** | Kavan Hada — kavanhada1903@gmail.com |
| **Members** | Aryan Sagar (dksagar1949@gmail.com), Dhruvang Upadhyay (dhruvangupadhyay10ascent@gmail.com) |

---

## 🎯 Problem Statement

Forensic document examiners in India face a growing caseload of forged certificates, degrees, property documents, and FIRs — the Education Ministry flagged 3,000+ fake degree cases in 2022 alone, and courts routinely receive forged property documents and altered FIRs. Examiners currently rely on ad-hoc notes rather than a structured, standards-linked workflow, which slows down turnaround and makes it harder to produce a consistent, defensible opinion.

---

## 💡 Solution

DocuVerity is a Bob-powered guided examination workflow. An examiner enters structured observations about a suspected forged document (font inconsistencies, signature mismatches, paper anomalies, ink spread, digital metadata flags). Bob then classifies the anomaly type, assigns a forgery confidence score, maps the findings to recognized questioned-document examination standards, and drafts a structured expert opinion report — turning a manual, unstructured process into a repeatable, inspectable pipeline.

---

## ✨ Key Features

- **Structured intake:** Captures observations across 5 forgery indicator categories (typography, signature, substrate, ink, digital metadata).
- **Anomaly classification + confidence scoring:** Weighted, rule-based scoring (0–100) with a transparent breakdown of which indicators drove the score.
- **Standards mapping:** Automatically links findings to relevant questioned-document examination standards.
- **Auto-drafted report:** Generates a structured expert opinion report (Markdown, exportable to PDF) ready for examiner review.
- **Genuine Bob/MCP integration:** Each stage (classify → score → map → draft) is its own MCP tool Bob calls — the reasoning is inspectable at every step, not one opaque prompt.

---

## 🛠️ Tech Stack

| Category | Technologies |
|---|---|
| **Languages** | Python 3.10+ |
| **Frameworks** | MCP (Model Context Protocol) Python SDK |
| **IBM Technologies** | IBM Bob (MCP client), watsonx.ai (optional report-language polishing) |
| **Databases** | None (stateless per-session examination) |
| **Other** | GitHub Actions |

---

## 📁 Repository Structure

```
├── src/                  # All source code
│   └── mcp_server/       # DocuVerity MCP server (4 tools) — see src/README.md
├── docs/                 # Written documentation
│   ├── problem-statement.md
│   ├── solution-overview.md
│   ├── architecture.md
│   └── setup-guide.md
├── demo/                 # Demo artifacts
│   ├── screenshots/      # App screenshots
│   └── demo-video-link.txt  # Link to demo video
├── presentation/         # Slide deck
└── submission.yaml       # Structured submission metadata
```

---

## ⚡ How to Run

> See [`docs/setup-guide.md`](docs/setup-guide.md) for full details, prerequisites, and troubleshooting.

```bash
# 1. Clone the repo
git clone https://github.com/[your-github-username]/bob-ai-hackathon-[your-team-name].git
cd bob-ai-hackathon-[your-team-name]

# 2. Install dependencies
cd src/mcp_server
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your values (watsonx.ai key is optional — see setup-guide.md)

# 4. Run the demo locally (no Bob/MCP wiring needed)
python server.py --demo

# 5. Or run as an MCP server for IBM Bob to call
python server.py
```

---

## 🖥️ Demo

| Artifact | Link |
|---|---|
| 📹 Demo Video | [See demo/demo-video-link.txt](demo/demo-video-link.txt) |
| 🌐 Live Demo | [See demo/live-demo-url.txt](demo/live-demo-url.txt) |
| 🖼️ Screenshots | [See demo/screenshots/](demo/screenshots/) |
| 📊 Presentation | [See presentation/slides.pdf](presentation/) |

---

## ⚠️ Known Limitations

- Anomaly classification and confidence scoring use transparent, documented heuristics rather than a trained forensic ML model — a deliberate scope choice for the hackathon timeframe, disclosed to the examiner in the generated report.
- Standard references mapped in the report are illustrative starting points and require validation by a certified document examiner before real court use.
- No persistence layer yet — each examination session is stateless (in-memory for the demo).

---

## 🏅 What We're Most Proud Of

The 4-stage MCP tool pipeline (classify → score → map-to-standard → draft-report) makes Bob's contribution inspectable at every step of a real forensic workflow, instead of hiding everything behind one generic prompt.

---
