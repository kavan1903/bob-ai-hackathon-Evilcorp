"""DocuVerity MCP server.

Exposes tools to IBM Bob over MCP:
  - analyze_image_tool
  - analyze_pdf_tool
  - examine_case_tool

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

from forensics import examine_case, render_report
from image_checker import analyze_image
from pdf_metadata import analyze_pdf
from watsonx_polish import polish_report

try:
    from mcp.server.fastmcp import FastMCP

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False


def _run_demo() -> None:
    print("=" * 70)
    print("DocuVerity — demo run")
    print("=" * 70)
    
    # 1. We would run check_image_tool or check_pdf_tool, but here we just
    # construct a case manually.
    
    case = {
        "case_id": "DEMO-CASE-2026",
        "document_type": "identity_document",
        "document_description": "Suspected forged ID card",
        "submitted_by": "Demo Mode",
        "examiner": {"name": "Demo Examiner", "designation": "System"},
        "findings": [
            {"indicator": "font_family_mismatch", "status": "present", "confidence": "high", "note": "Font differs from template"},
            {"indicator": "spacing_irregular", "status": "present", "confidence": "moderate", "note": "Kerning is off"}
        ]
    }
    
    print("Running examine_case...")
    result = examine_case(case)
    
    print("Drafting report...")
    report = render_report(case, result)
    
    # Polish report if watsonx is configured
    try:
        report = polish_report(report)
    except Exception as e:
        pass # Ignore polish errors in demo if API key isn't set
        
    print("-" * 70)
    print(report)


def _build_mcp_server() -> "FastMCP":
    mcp = FastMCP("docuverity")

    @mcp.tool()
    def check_image_tampering_tool(image_path: str) -> dict:
        """Analyzes an image file for tampering using Error Level Analysis and EXIF checks."""
        return analyze_image(image_path)

    @mcp.tool()
    def check_pdf_metadata_tool(pdf_path: str, stated_issue_date: str = "") -> dict:
        """Analyzes a PDF file for hidden edits, re-saves, and creation date anomalies."""
        return analyze_pdf(pdf_path, stated_issue_date=stated_issue_date)

    @mcp.tool()
    def examine_case_tool(case_id: str, document_type: str, findings: list[dict], pdf_file: str = "") -> str:
        """
        Run the full forensic evaluation pipeline and draft a structured expert opinion report.
        
        findings: list of dicts with keys 'indicator', 'status', 'confidence', 'note'.
        indicator must map to one of the known INDICATORS (e.g., 'font_family_mismatch', 'signature_identical_overlay', etc).
        """
        case = {
            "case_id": case_id,
            "document_type": document_type,
            "pdf_file": pdf_file,
            "findings": findings,
            "examiner": {"name": "Bob", "designation": "AI Assistant"}
        }
        
        result = examine_case(case)
        report = render_report(case, result)
        
        try:
            report = polish_report(report)
        except Exception:
            pass
            
        return report

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
