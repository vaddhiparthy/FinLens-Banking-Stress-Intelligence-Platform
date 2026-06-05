"""B1 smoke-pull: can we fetch ORIGINALLY-FILED Call Report bulk data from the FFIEC
CDR Public Data Distribution at $0, scriptably? This is the GO/NO-GO checkpoint.

The CDR bulk page is an ASP.NET form with a cascading product->dates dropdown:
  1. GET the page -> __VIEWSTATE / __VIEWSTATEGENERATOR.
  2. POST selecting product "Call Reports -- Single Period" (autopostback) -> dates.
  3. POST product + a chosen period + TSV format + Download -> a .zip of TSV schedules.

Success = a real zip with Call Report schedule TSVs (RC, RCN, etc.) for a chosen
period, parseable, with a RSSD/IDRSSD key we can map to FDIC CERT. Prints a verdict.
"""

from __future__ import annotations

import io
import re
import sys
import zipfile
from pathlib import Path

import requests

URL = "https://cdr.ffiec.gov/public/PWS/DownloadBulkData.aspx"
PRODUCT = "ReportingSeriesSinglePeriod"  # Call Reports -- Single Period (originally filed)
OUT = Path(__file__).resolve().parents[2] / "data" / "ffiec_probe"
OUT.mkdir(parents=True, exist_ok=True)


def _hidden(html: str) -> dict:
    fields = {}
    for name in ("__VIEWSTATE", "__VIEWSTATEGENERATOR", "__EVENTVALIDATION"):
        m = re.search(rf'id="{name}"\s+value="([^"]*)"', html)
        if m:
            fields[name] = m.group(1)
    return fields


def _dates(html: str) -> list[str]:
    m = re.search(r'DatesDropDownList.*?</select>', html, re.S)
    if not m:
        return []
    return [v for v in re.findall(r'<option[^>]*value="([^"]*)"', m.group(0)) if v]


def main() -> int:
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0 (research; FinLens portfolio; $0 public data)"})
    print("[1] GET form...", flush=True)
    r = s.get(URL, timeout=30)
    r.raise_for_status()
    f = _hidden(r.text)
    print("    viewstate len:", len(f.get("__VIEWSTATE", "")), flush=True)

    print("[2] POST product selection (autopostback) to populate dates...", flush=True)
    data = {
        "__EVENTTARGET": "ctl00$MainContentHolder$ListBox1",
        "__EVENTARGUMENT": "",
        "ctl00$MainContentHolder$ListBox1": PRODUCT,
        **f,
    }
    r2 = s.post(URL, data=data, timeout=60)
    r2.raise_for_status()
    f2 = _hidden(r2.text)
    dates = _dates(r2.text)
    print(f"    dates returned: {len(dates)}; sample: {dates[:4]}", flush=True)
    if not dates:
        print("NO-GO: product postback did not populate periods (form mechanism changed).")
        return 2

    period = dates[0]  # most recent period
    print(f"[3] POST download for period {period} (TSV)...", flush=True)
    data3 = {
        "ctl00$MainContentHolder$ListBox1": PRODUCT,
        "ctl00$MainContentHolder$DatesDropDownList": period,
        "ctl00$MainContentHolder$FormatType": "TSVRadioButton",
        "ctl00$MainContentHolder$TabStrip1$Download_0": "Download",
        "__EVENTTARGET": "",
        "__EVENTARGUMENT": "",
        **f2,
    }
    r3 = s.post(URL, data=data3, timeout=180)
    ct = r3.headers.get("Content-Type", "")
    cd = r3.headers.get("Content-Disposition", "")
    print(f"    status {r3.status_code} | type {ct} | size {len(r3.content):,} | {cd[:80]}",
          flush=True)
    if r3.status_code != 200 or len(r3.content) < 1000:
        print("NO-GO: download did not return a payload.")
        return 3

    is_zip = r3.content[:2] == b"PK" or "zip" in ct.lower()
    if not is_zip:
        snippet = r3.content[:200].decode("utf-8", "ignore")
        print("NO-GO: response is not a zip. Head:", snippet)
        return 4

    zpath = OUT / f"call_{period}.zip"
    zpath.write_bytes(r3.content)
    with zipfile.ZipFile(io.BytesIO(r3.content)) as z:
        names = z.namelist()
        print(f"    zip OK: {len(names)} files. sample: {names[:5]}", flush=True)
        # peek a schedule for the RSSD key + a couple of fields
        tsvs = [n for n in names if n.lower().endswith(".txt") or n.lower().endswith(".tsv")]
        key_found = False
        if tsvs:
            with z.open(tsvs[0]) as fh:
                head = fh.read(1500).decode("utf-8", "ignore")
            hdr = head.splitlines()[:2]
            print("    first schedule:", tsvs[0], flush=True)
            print("    header line:", hdr[0][:160] if hdr else "", flush=True)
            key_found = bool(re.search(r"IDRSSD|RSSD", head, re.I))
    print(f"\nGO: originally-filed Call Report bulk pull works at $0. "
          f"period={period}, files={len(names)}, RSSD key present={key_found}, saved {zpath}",
          flush=True)
    print("NOTE: full B1 (multi-period pull 2008-2026 + RSSD->CERT crosswalk + "
          "point-in-time feature rebuild) is still days of ETL; this only proves feasibility.",
          flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
