"""B1 step 1: download originally-filed FFIEC CDR Call Report bulk for every quarter
2008Q1..2026Q1 (TSV). Idempotent (skips existing), polite (sequential), $0.

Saves one zip per period to data/ffiec_raw/call_<YYYYMMDD>.zip.
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path

import requests

URL = "https://cdr.ffiec.gov/public/PWS/DownloadBulkData.aspx"
PRODUCT = "ReportingSeriesSinglePeriod"
RAW = Path(__file__).resolve().parents[2] / "data" / "ffiec_raw"
RAW.mkdir(parents=True, exist_ok=True)


def _hidden(html: str) -> dict:
    d = {}
    for n in ("__VIEWSTATE", "__VIEWSTATEGENERATOR", "__EVENTVALIDATION"):
        m = re.search(rf'id="{n}"\s+value="([^"]*)"', html)
        if m:
            d[n] = m.group(1)
    return d


def _session_with_dates():
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0 (FinLens research; $0 public data)"})
    r = s.get(URL, timeout=30)
    f = _hidden(r.text)
    r2 = s.post(URL, data={
        "__EVENTTARGET": "ctl00$MainContentHolder$ListBox1", "__EVENTARGUMENT": "",
        "ctl00$MainContentHolder$ListBox1": PRODUCT, **f}, timeout=60)
    f2 = _hidden(r2.text)
    m = re.search(r'DatesDropDownList.*?</select>', r2.text, re.S)
    opts = re.findall(r'<option[^>]*value="([^"]*)"[^>]*>([^<]*)', m.group(0))
    return s, f2, opts


def _download(s, f2, period_val, date_text) -> tuple[bool, int]:
    data = {
        "ctl00$MainContentHolder$ListBox1": PRODUCT,
        "ctl00$MainContentHolder$DatesDropDownList": period_val,
        "ctl00$MainContentHolder$FormatType": "TSVRadioButton",
        "ctl00$MainContentHolder$TabStrip1$Download_0": "Download",
        "__EVENTTARGET": "", "__EVENTARGUMENT": "", **f2,
    }
    r = s.post(URL, data=data, timeout=240)
    if r.status_code == 200 and r.content[:2] == b"PK" and len(r.content) > 1000:
        mm, dd, yyyy = date_text.split("/")
        out = RAW / f"call_{yyyy}{mm}{dd}.zip"
        out.write_bytes(r.content)
        return True, len(r.content)
    return False, len(r.content)


def main() -> int:
    s, f2, opts = _session_with_dates()
    # quarters 2008..2026
    want = [(v, t) for v, t in opts if re.search(r"/(20(0[89]|1\d|2[0-6]))$", t)]
    want = sorted(want, key=lambda x: (x[1][6:], x[1][0:2]))  # chrono
    print(f"{len(want)} periods to fetch (2008-2026)", flush=True)
    ok = skipped = failed = 0
    for v, t in want:
        mm, dd, yyyy = t.split("/")
        out = RAW / f"call_{yyyy}{mm}{dd}.zip"
        if out.exists() and out.stat().st_size > 1000:
            skipped += 1
            continue
        for attempt in range(3):
            try:
                done, size = _download(s, f2, v, t)
                if done:
                    ok += 1
                    print(f"  {t} -> {size:,} bytes", flush=True)
                    break
                # refresh session/viewstate on failure
                s, f2, _ = _session_with_dates()
            except Exception as exc:
                print(f"  {t} attempt {attempt} error: {exc}", flush=True)
                time.sleep(2)
                s, f2, _ = _session_with_dates()
        else:
            failed += 1
            print(f"  {t} FAILED", flush=True)
        time.sleep(0.5)
    print(f"\ndone: {ok} downloaded, {skipped} already present, {failed} failed; dir {RAW}",
          flush=True)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
