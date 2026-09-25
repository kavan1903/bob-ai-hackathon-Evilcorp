"""Optional watsonx.ai report-language polishing.

If WATSONX_API_KEY / WATSONX_PROJECT_ID are not configured, polish_report()
returns the input unchanged so the rest of the pipeline works fully offline.
This keeps the forensic judgment (classification/scoring/mapping) auditable
and independent of any external API call.
"""
from __future__ import annotations

import os

try:
    import requests
except ImportError:
    requests = None


def polish_report(report_markdown: str) -> str:
    api_key = os.getenv("WATSONX_API_KEY")
    project_id = os.getenv("WATSONX_PROJECT_ID")
    base_url = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")

    if not api_key or not project_id or requests is None:
        return report_markdown

    try:
        # NOTE: illustrative call shape — adjust to the exact watsonx.ai
        # text-generation endpoint/model your IBM Cloud project uses.
        response = requests.post(
            f"{base_url}/ml/v1/text/generation?version=2024-05-01",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "project_id": project_id,
                "model_id": "ibm/granite-13b-instruct-v2",
                "input": (
                    "Rewrite the following forensic report in clear, formal "
                    "expert-opinion language without changing any facts, "
                    "figures, or conclusions:\n\n" + report_markdown
                ),
                "parameters": {"max_new_tokens": 800},
            },
            timeout=15,
        )
        response.raise_for_status()
        generated = response.json()["results"][0]["generated_text"]
        return generated.strip() or report_markdown
    except Exception:
        # Never let an optional polishing step break the core pipeline.
        return report_markdown
