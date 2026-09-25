"""DocuVerity MCP server.

Exposes 4 tools to IBM Bob over MCP:
  - classify_anomaly
  - score_forgery_confidence
  - map_to_examination_standard
  - draft_expert_report

Run modes:
  python server.py            # start as an MCP server (stdio transport) for Bob
  python server.py --demo     # run a scripted example locally, no MCP/Bob needed
"""
from __future__ import annotations

import os
import sys

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from forensics import (
    Observation,
    ObservationSet,
    classify_anomaly,
    score_forgery_confidence,
    map_to_examination_standard,
    draft_expert_report,
)
from watsonx_polish import polish_report

try:
    from mcp.server.fastmcp import FastMCP

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False


def _build_observation_set(document_id: str, observations: list[dict]) -> ObservationSet:
    return ObservationSet(
        document_id=document_id,
        observations=[
            Observation(
                category=o["category"],
                detail=o.get("detail", ""),
                severity=o.get("severity", "moderate"),
            )
            for o in observations
        ],
    )


def run_full_pipeline(document_id: str, observations: list[dict], examiner_name: str | None = None) -> dict:
    """Runs all 4 stages end-to-end. Used by both the demo and the MCP tools."""
    obs_set = _build_observation_set(document_id, observations)
    anomaly_type = classify_anomaly(obs_set)
    confidence = score_forgery_confidence(obs_set)
    standards = map_to_examination_standard(anomaly_type)
    report = draft_expert_report(obs_set, anomaly_type, confidence, standards, examiner_name)
    report = polish_report(report)
    return {
        "anomaly_type": anomaly_type,
        "confidence": confidence,
        "standards": standards,
        "report": report,
    }


def _run_demo() -> None:
    sample_observations = [
        {
            "category": "signature_mismatch",
            "detail": "Stroke pattern and pen pressure inconsistent with exemplar signatures",
            "severity": "high",
        },
        {
            "category": "paper_anomaly",
            "detail": "Substrate fluoresces differently under UV compared to genuine stock",
            "severity": "moderate",
        },
        {
            "category": "metadata_flag",
            "detail": "PDF creation timestamp postdates the document's stated issue date",
            "severity": "high",
        },
    ]
    result = run_full_pipeline("DOC-2026-0142", sample_observations, examiner_name="Demo Examiner")
    print("=" * 70)
    print("DocuVerity — demo run")
    print("=" * 70)
    print(f"Anomaly type:        {result['anomaly_type']}")
    print(f"Confidence score:    {result['confidence']['score']} / 100")
    print(f"Score breakdown:     {result['confidence']['breakdown']}")
    print(f"Mapped standards:    {result['standards']}")
    print("-" * 70)
    print(result["report"])


def _build_mcp_server() -> "FastMCP":
    mcp = FastMCP("docuverity")

    @mcp.tool()
    def classify_anomaly_tool(document_id: str, observations: list[dict]) -> str:
        """Classify the forgery anomaly type from a list of flagged observations.

        Each observation is a dict: {category, detail, severity}. category must
        be one of: font_inconsistency, signature_mismatch, paper_anomaly,
        ink_spread_anomaly, metadata_flag.
        """
        obs_set = _build_observation_set(document_id, observations)
        return classify_anomaly(obs_set)

    @mcp.tool()
    def score_forgery_confidence_tool(document_id: str, observations: list[dict]) -> dict:
        """Score forgery confidence (0-100) for a document given flagged observations."""
        obs_set = _build_observation_set(document_id, observations)
        return score_forgery_confidence(obs_set)

    @mcp.tool()
    def map_to_examination_standard_tool(anomaly_type: str) -> list[str]:
        """Map an anomaly type to relevant questioned-document examination standards."""
        return map_to_examination_standard(anomaly_type)

    @mcp.tool()
    def draft_expert_report_tool(
        document_id: str, observations: list[dict], examiner_name: str = ""
    ) -> str:
        """Run the full pipeline and draft a structured expert opinion report."""
        result = run_full_pipeline(document_id, observations, examiner_name or None)
        return result["report"]

    return mcp


if __name__ == "__main__":
    if "--demo" in sys.argv:
        _run_demo()
    elif MCP_AVAILABLE:
        _build_mcp_server().run()
    else:
        print(
            "The 'mcp' package is not installed, so this can't run as an MCP "
            "server. Install it with: pip install -r requirements.txt\n"
            "Running in --demo mode instead so you can still see the pipeline work.\n"
        )
        _run_demo()
