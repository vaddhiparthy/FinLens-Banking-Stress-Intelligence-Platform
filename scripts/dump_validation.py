"""Run every validation live, capture the RAW output, and write one evidence markdown to the
Desktop (overriding the prior document). No summaries — actual command output, fenced."""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PY = str(REPO / ".venv" / "Scripts" / "python.exe")
DESK = [Path(r"C:\Users\vaddh\OneDrive\Desktop\FinLens_End_to_End.md"),
        Path(r"C:\Users\vaddh\Desktop\FinLens_End_to_End.md")]


def run(cmd, cwd=REPO, timeout=600):
    try:
        r = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                           timeout=timeout, encoding="utf-8", errors="replace")
        out = (r.stdout or "") + (("\n[stderr]\n" + r.stderr) if r.stderr.strip() else "")
        return out.strip() or "(no output)"
    except Exception as exc:  # noqa: BLE001
        return f"(command failed: {exc})"


# (section title, shell command list, cwd, timeout)
CHECKS = [
    ("Git: HEAD + recent commits", [PY, "-c",
     "import subprocess;print(subprocess.run(['git','log','--oneline','-10'],capture_output=True,text=True).stdout)"], REPO, 60),
    ("Git: served-model freeze commit 7473608", ["git", "log", "-1", "7473608"], REPO, 60),
    ("Git: working tree status", ["git", "status", "--short"], REPO, 60),
    ("pytest tests/ ml/tests/ -q (FULL)", [PY, "-m", "pytest", "tests/", "ml/tests/", "-q"], REPO, 300),
    ("Great Expectations validate.py", [PY, "great_expectations/validate.py"], REPO, 120),
    ("DuckDB live counts (panel, failures, OOT, SVB)", [PY, "-c",
     "import sys;sys.path[:0]=['','src','ml'];import warnings;warnings.filterwarnings('ignore');import duckdb,json;"
     "c=duckdb.connect('.duckdb/finlens.duckdb',read_only=True);"
     "print('ml.training_dataset:',c.execute('select count(*) rows,count(distinct cert) banks,min(quarter) q0,max(quarter) q1 from ml.training_dataset').df().to_dict(orient='records'));"
     "print('marts.fct_bank_failures (all FDIC failures):',c.execute('select count(*) from marts.fct_bank_failures').fetchone()[0]);"
     "m=json.load(open('ml/artifacts/metrics_h4.json'));print('OOT test positives (66):',m.get('test_positives'),'| train',m.get('n_train'),'| test',m.get('n_test'));"
     "t=m['oot_test']['calibrated_lgbm'];print('OOT PR-AUC',round(t['pr_auc'],4),'ROC',round(t['roc_auc'],4),'recall@200',round(t['recall_at_k'],4),'ECE',m.get('oot_calibration',{}).get('ece'));"
     "print('SVB row:',c.execute(\"select cert,bank_name,quarter from ml.training_dataset where cert=24735 order by quarter desc limit 1\").df().to_dict(orient='records'))"], REPO, 120),
    ("panel_facts.json", ["cat", "ml/artifacts/panel_facts.json"], REPO, 30),
    ("great_expectations/validation_result.json (per-expectation)", ["cat", "great_expectations/validation_result.json"], REPO, 30),
    ("Lighthouse accessibility/perf/bp/seo per page", [PY, "-c",
     "import json,glob;\n"
     "[print(f.split(chr(92))[-1].split('/')[-1], {k[:4]:(round(v['score']*100) if v.get('score') is not None else 'n/a') for k,v in json.load(open(f))['categories'].items()}) for f in sorted(glob.glob('audit/lighthouse/*.json'))]"], REPO, 60),
    ("axe violations per page", [PY, "-c",
     "import json,glob;\n[print(f.split('/')[-1].split(chr(92))[-1], 'violations=', json.load(open(f)).get('nViolations'), 'passes=', json.load(open(f)).get('passes')) for f in sorted(glob.glob('audit/axe/*.json'))]"], REPO, 60),
    ("Playwright results.xml (testsuite header)", [PY, "-c",
     "import re;s=open('audit/playwright/results.xml',encoding='utf-8').read();import sys;[print(m) for m in re.findall(r'<testsuites[^>]*>', s)[:1]];print('testcases:',len(re.findall(r'<testcase',s)),'failures:',len(re.findall(r'<failure',s)))"], REPO, 60),
    ("FULL assertion E2E (surfaces + functional + chat + report)",
     ["npx", "playwright", "test", "--config", "playwright.config.mjs",
      "surfaces.spec.mjs", "functional_sweep.spec.mjs", "chat_report.spec.mjs", "report_open.spec.mjs"],
     REPO / "audit" / "e2e", 600),
    ("Reviewer sign-off verdicts (audit/signoffs/)", [PY, "-c",
     "import glob;\n"
     "[print('---',f.split('/')[-1].split(chr(92))[-1]) or [print('  '+l.strip()) for l in open(f,encoding='utf-8') if l.strip().upper().startswith('VERDICT')] for f in sorted(glob.glob('audit/signoffs/*.md'))]"], REPO, 60),
    ("dbt build summary (live run_results)", [PY, "-c",
     "import sys;sys.path[:0]=['','src','ml'];from finlens.evidence import dbt_artifact_summary;import json;print(json.dumps(dbt_artifact_summary(),indent=1))"], REPO, 60),
    ("Pipeline status (data/state/pipeline_status.json)", [PY, "-c",
     "import json;d=json.load(open('data/state/pipeline_status.json'));[print(k,'->',v.get('status'),'| last_run:',str(v.get('last_run'))[:19],'| rows:',v.get('rows')) for k,v in d.items()]"], REPO, 30),
    ("Today's ingestion partitions (proof of real run)", ["bash", "-lc",
     "ls -d data/raw/source=*/ingestion_date=$(date +%F) 2>/dev/null || ls -d data/raw/source=*/ 2>/dev/null | tail -8"], REPO, 30),
    ("No-fake-data guard: grep load_demo / datasets / mock (excl venv,node_modules)", ["bash", "-lc",
     "grep -rn 'load_demo\\|finlens.datasets\\|finlens_data_mode == .mock' --include=*.py src/ streamlit_app/ api/ ml/ rag/ 2>/dev/null | grep -v node_modules || echo 'NONE FOUND (no fabricated-data path)'"], REPO, 60),
    ("Wiki: article count + zero 'two surfaces'", [PY, "-c",
     "import sys;sys.path[:0]=['','src','ml'];import warnings;warnings.filterwarnings('ignore');import re,glob;"
     "from streamlit_app.lib import wiki_structure as ws;print('wiki articles:',len(ws.ARTICLES));"
     "print('two-surfaces phrases:',sum(len(re.findall(r'two surfaces|2 surfaces|both surfaces',open(f,encoding='utf-8').read(),re.I)) for f in glob.glob('streamlit_app/lib/wiki_*.py')))"], REPO, 60),
    ("Audit artifacts present", ["bash", "-lc",
     "echo 'signoffs:'; ls audit/signoffs/; echo; echo 'ceiling screenshots:'; ls audit/screenshots/ceiling/*.png | wc -l; echo 'certifications:'; ls audit/CERTIFICATION.md audit/UI_CEILING_SIGNOFF.md audit/FACT_CHECK.md"], REPO, 30),
]


def main():
    parts = []
    parts.append("# FinLens — Raw Validation Evidence Dump")
    parts.append("")
    parts.append("Raw output of every validation, run live against the repository. This is the "
                 "territory, not a summary: each section below is the actual command and its raw "
                 "output. Reproduce any line by running the command shown.")
    parts.append("")
    parts.append(f"- Repo: `{REPO}`")
    parts.append(f"- Generated: {datetime.now().isoformat(timespec='seconds')} (local)")
    parts.append("- Served model is pinned at commit `7473608` (2026-06-05); repo HEAD is shown below.")
    parts.append("- 574 = all FDIC failures in the raw list since 2000; 66 = the subset inside the "
                 "embargoed out-of-time test window (the model's evaluation universe).")
    parts.append("")
    for i, (title, cmd, cwd, to) in enumerate(CHECKS, 1):
        shown = " ".join(c if c not in (PY,) else "python" for c in cmd) if isinstance(cmd, list) else cmd
        out = run(cmd, cwd=cwd, timeout=to)
        parts.append(f"## {i}. {title}")
        parts.append(f"`$ {shown}`  (cwd: `{cwd}`)")
        parts.append("```")
        parts.append(out[:12000])
        parts.append("```")
        parts.append("")
        print(f"[{i}/{len(CHECKS)}] {title}: captured {len(out)} chars", flush=True)
    md = "\n".join(parts)
    for d in DESK:
        try:
            d.write_text(md, encoding="utf-8")
            print("wrote", d)
        except Exception as exc:  # noqa: BLE001
            print("FAILED to write", d, exc)
    print("TOTAL", len(md), "chars")


if __name__ == "__main__":
    sys.exit(main())
