"""Score the 5-category pipeline against a ground-truth manifest.

    python samples/evaluate_testset.py samples/testdocs sig_exemplar_A.png
    python samples/evaluate_testset.py samples/heldout  sig_exemplar_B.png
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from doc_checks.pipeline import CATEGORIES, analyze_document  # noqa: E402

SHORT = {"typography": "font", "signature": "sign", "substrate": "paper", "ink": "ink", "digital": "digit"}
SYM = {"flag": "FLAG", "pass": "ok", "skipped": "-"}


def evaluate(folder: Path, exemplar: str) -> dict:
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    tp = fp = fn = tn = 0
    rows = []
    print(f"{'file':32s} {'expected':18s} " + " ".join(f"{SHORT[c]:>6s}" for c in CATEGORIES) + "    ms  result")
    for d in manifest["documents"]:
        t = time.perf_counter()
        r = analyze_document(str(folder / d["file"]), exemplar_path=str(folder / exemplar),
                             stated_issue_date="2023-06-15" if d["file"].endswith(".pdf") else "")
        ms = (time.perf_counter() - t) * 1000
        got = {c: r["summary"][c]["status"] for c in CATEGORIES}
        exp = set(d["expected"])
        for c in CATEGORIES:
            flagged, should = got[c] == "flag", c in exp
            tp += flagged and should; fp += flagged and not should
            fn += should and not flagged; tn += (not flagged) and (not should)
        ok = all((got[c] == "flag") == (c in exp) for c in CATEGORIES)
        rows.append({"file": d["file"], "ok": ok})
        print(f"{d['file']:32s} {','.join(d['expected']) or '-':18s} "
              + " ".join(f"{SYM[got[c]]:>6s}" for c in CATEGORIES) + f" {ms:5.0f}  {'OK' if ok else 'WRONG'}")
        if not ok:
            for c in r["checks"]:
                if c["result"] in ("flag", "pass") and (c["result"] == "flag") != (c["category"] in exp):
                    print(f"      {c['result']:4s} {c['category']}/{c['check']}: {c['detail'][:130]}")
    summary = {"documents": len(rows), "documents_correct": sum(r["ok"] for r in rows),
               "category_decisions": tp + fp + fn + tn, "true_flags": tp, "false_alarms": fp,
               "missed": fn, "correct_passes": tn}
    print(json.dumps(summary))
    return summary


if __name__ == "__main__":
    evaluate(Path(sys.argv[1]), sys.argv[2])
