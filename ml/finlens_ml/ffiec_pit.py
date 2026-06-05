"""B1: point-in-time feature build from ORIGINALLY-FILED FFIEC Call Reports.

Parses the FFIEC CDR bulk TSV zips (data/ffiec_raw/call_YYYYMMDD.zip) into the SAME
raw-field schema the FDIC panel uses, so finlens_ml.features.build_features runs
unchanged. The difference vs the shipped panel is INTEGRITY: these are the values as
ORIGINALLY FILED for that quarter, not the FDIC `/financials` currently-restated
values, removing restatement look-ahead.

MDRM mapping is validated field-by-field against the FDIC panel for recent (not-yet-
restated) quarters by `validate()`. Consolidated (RCFD/RCFA/RCFN) is preferred with
domestic (RCON/RCOA) fallback. Derived ratios use transparent, documented formulas
(annualized YTD income over RC-K average assets); capital ratios use the values the
bank reported directly on Schedule RC-R. $0, public data only.
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path(__file__).resolve().parents[1].parent / "data" / "ffiec_raw"


_LABELS: dict[str, str] = {}  # MDRM code -> human label, captured at read time


def _read(zf: zipfile.ZipFile, part: str) -> pd.DataFrame | None:
    names = [n for n in zf.namelist() if part in n]
    if not names:
        return None
    frames = []
    for name in names:  # some schedules ship as "(1 of 2)"/"(2 of 2)"
        with zf.open(name) as fh:
            codes = fh.readline().decode("utf-8", "ignore").rstrip("\n").split("\t")
            labs = fh.readline().decode("utf-8", "ignore").rstrip("\n").split("\t")
        for c, lab in zip(codes, labs):
            _LABELS[c.replace('"', "").strip().upper()] = lab.upper()
        with zf.open(name) as fh:
            frames.append(pd.read_csv(fh, sep="\t", dtype=str, skiprows=[1], low_memory=False))
    df = frames[0] if len(frames) == 1 else frames[0].merge(
        pd.concat(frames[1:]), on=[c for c in frames[0].columns if "IDRSSD" in c], how="outer",
        suffixes=("", "_dup"))
    idc = [c for c in df.columns if "IDRSSD" in c][0]
    df = df.rename(columns={idc: "IDRSSD"})
    df["IDRSSD"] = pd.to_numeric(df["IDRSSD"], errors="coerce")
    df = df.dropna(subset=["IDRSSD"]).drop_duplicates(subset=["IDRSSD"], keep="first")
    return df


def _num(df: pd.DataFrame, *codes: str) -> pd.Series:
    """First matching MDRM code (consolidated preferred), coerced numeric; later codes
    fill NaNs of earlier ones."""
    out = pd.Series(np.nan, index=df.index)
    for code in codes:
        cols = [c for c in df.columns if c.replace('"', "").strip().upper().startswith(code)]
        if cols:
            raw = df[cols[0]].astype(str).str.replace("%", "", regex=False).str.replace(
                ",", "", regex=False).str.strip()
            out = out.fillna(pd.to_numeric(raw, errors="coerce"))
    return out


_NC_EXCLUDE = ("30-89", "30 THRU", "30 TO 89", "PAST DU 30", "PAST DUE 30", "PD 30",
               "RESTRUCTURED", "RSTRCTD", "HELD FOR SALE", "H-F-S", "HLD FOR SALE",
               "H F S", "HFS", "DERIVED", "ADDITIONS", "MEMORAND", "OTHER ASSETS",
               "TOTAL")


def _is_noncurrent_label(lab: str) -> bool:
    if not lab or any(x in lab for x in _NC_EXCLUDE):
        return False
    return ("NONACCRUAL" in lab or "PAST DU 90" in lab or "PAST DUE 90" in lab
            or "PD 90" in lab or "PD GE 90" in lab or "90 DYS OR MO" in lab
            or "90 DAYS" in lab or "90DYS" in lab or "90 MOR" in lab or "90DAY" in lab
            or ">=90" in lab or ">= 90" in lab or ">90" in lab or "90 DY" in lab)


def _noncurrent(RCN: pd.DataFrame) -> pd.Series:
    """Total noncurrent loans = nonaccrual + 90+-days-accruing. Use the official total
    codes (RCFD/RCON 1403+1407) where present (2014+); pre-2014 vintages lack them, so
    sum the per-category nonaccrual/90+ columns by LABEL (codes vary by year), picking
    one filer-domain per item to avoid RCFD/RCON double-counting. The category sum is
    validated against the official total where both exist (see validate_noncurrent)."""
    na = _num(RCN, "RCFD1403", "RCON1403")
    pd90 = _num(RCN, "RCFD1407", "RCON1407")
    official = na.add(pd90, fill_value=0)
    if official.notna().any():
        return official
    # pre-2014 category sum, deduped per 4-char item (prefer RCFD > RCON > RCFA)
    by_item: dict[str, str] = {}
    for c in RCN.columns:
        if not _is_noncurrent_label(_LABELS.get(str(c).upper(), "")):
            continue
        item = str(c)[-4:]
        cur = by_item.get(item)
        if cur is None or (str(c).upper().startswith("RCFD") and not cur.upper().startswith("RCFD")):
            by_item[item] = c
    if not by_item:
        return pd.Series(np.nan, index=RCN.index)
    total = pd.Series(0.0, index=RCN.index)
    any_val = pd.Series(False, index=RCN.index)
    for col in by_item.values():
        v = pd.to_numeric(RCN[col].astype(str).str.replace(",", "", regex=False),
                          errors="coerce")
        total = total.add(v, fill_value=0)
        any_val = any_val | v.notna()
    return total.where(any_val)  # NaN if the bank reported none of these columns


def _qnum(repdte: str) -> int:
    return {"03": 1, "06": 2, "09": 3, "12": 4}[repdte[4:6]]


def parse_period(zip_path: Path) -> pd.DataFrame:
    repdte = re.search(r"call_(\d{8})", zip_path.name).group(1)  # YYYYMMDD
    yyyy, mm = repdte[:4], repdte[4:6]
    quarter = f"{yyyy}Q{_qnum(repdte)}"
    qnum = _qnum(repdte)
    ann = 4.0 / qnum  # YTD income annualization factor

    with zipfile.ZipFile(zip_path) as zf:
        por = _read(zf, "Bulk POR")
        rc = _read(zf, "Schedule RC ")
        rcn = _read(zf, "Schedule RCN")
        rcr = _read(zf, "Schedule RCRI")
        if rcr is None:  # pre-2014 Basel III: single "Schedule RCR"
            rcr = _read(zf, "Schedule RCR ")
        rck = _read(zf, "Schedule RCK")
        ri = _read(zf, "Schedule RI ")
        rib = _read(zf, "Schedule RIBI")
        rco = _read(zf, "Schedule RCO")
        rce = _read(zf, "Schedule RCE")

    cert_col = [c for c in por.columns if "Certificate" in c][0]
    name_col = [c for c in por.columns if "Financial Institution Name" in c]
    state_col = [c for c in por.columns if "State" in c and "Abbrev" in c] or \
        [c for c in por.columns if c.strip() == "Financial Institution State"]
    base = por[["IDRSSD", cert_col]].rename(columns={cert_col: "cert"})
    base["cert"] = pd.to_numeric(base["cert"], errors="coerce")
    base["bank_name"] = por[name_col[0]] if name_col else None
    base["state"] = por[state_col[0]] if state_col else None

    base = base.set_index("IDRSSD")

    def J(df):  # align a schedule to the POR index; missing schedule -> all-NaN frame
        if df is None:
            return pd.DataFrame(index=base.index)
        return df.set_index("IDRSSD").reindex(base.index)
    RC, RCN, RCR, RCK, RI, RIB, RCO, RCE = map(J, [rc, rcn, rcr, rck, ri, rib, rco, rce])
    out = base.copy()

    # ---- levels ($ thousands) ----
    out["ASSET"] = _num(RC, "RCFD2170", "RCON2170")
    out["EQ"] = _num(RC, "RCFD3210", "RCON3210")
    out["LNLSGR"] = _num(RC, "RCFDB528", "RCONB528", "RCFD2122", "RCON2122")
    out["LNATRES"] = _num(RC, "RCFD3123", "RCON3123")
    out["LNLSNET"] = out["LNLSGR"] - out["LNATRES"].fillna(0)
    dep_dom = _num(RC, "RCON2200")
    dep_for = _num(RC, "RCFN2200").fillna(0)
    out["DEP"] = dep_dom.fillna(_num(RC, "RCFD2200")) + dep_for
    out["CHBAL"] = _num(RC, "RCON0071").fillna(0) + _num(RC, "RCON0081").fillna(0)
    htm = _num(RC, "RCFDJJ34", "RCONJJ34", "RCFD1754", "RCON1754")
    afs = _num(RC, "RCFD1773", "RCON1773")
    out["SCHA"], out["SCAF"] = htm, afs
    out["SC"] = htm.fillna(0) + afs.fillna(0)

    # ---- asset quality ----
    # noncurrent = nonaccrual + 90+-days-accruing. Official total (2014+) or a
    # label-based per-category sum for pre-2014 vintages (see _noncurrent).
    out["P9LNLS"] = _noncurrent(RCN)
    nco = (_num(RIB, "RIAD4635").fillna(0) - _num(RIB, "RIAD4605").fillna(0)) * ann
    out["NTLNLSR"] = (nco / out["LNLSGR"].where(out["LNLSGR"] > 0)) * 100

    # ---- earnings (YTD income annualized over RC-K average assets) ----
    avg_assets = _num(RCK, "RCFD3368", "RCON3368").where(lambda s: s > 0)
    avg_assets = avg_assets.fillna(out["ASSET"].where(out["ASSET"] > 0))
    ni = _num(RI, "RIAD4340")
    nii = _num(RI, "RIAD4074")          # net interest income
    noni_inc = _num(RI, "RIAD4079")     # noninterest income
    noni_exp = _num(RI, "RIAD4093")     # noninterest expense
    out["ROA"] = (ni * ann) / avg_assets * 100
    out["ROE"] = (ni * ann) / out["EQ"].where(out["EQ"] > 0) * 100
    out["NIMY"] = (nii * ann) / avg_assets * 100  # over avg assets (transparent proxy)
    out["EEFFR"] = noni_exp / (nii + noni_inc).where((nii + noni_inc) > 0) * 100

    # ---- capital (bank-reported RC-R ratios) ----
    # capital: post-2014 Basel III uses RCOA/RCFA; pre-2014 uses RCON (domestic) codes
    out["RBC1RWAJ"] = _num(RCR, "RCOA7206", "RCFA7206", "RCON7206")   # tier-1 risk-based ratio
    out["RBCT1J"] = _num(RCR, "RCOA8274", "RCFA8274", "RCON8274")     # tier-1 capital $
    # tier1_leverage in features.py = RBCT1J/ASSET*100; RC-R reports the leverage ratio
    # directly (7204). Provide RBCT1J so features.py formula holds; level is consistent.

    # ---- deposits detail ----
    out["BRO"] = _num(RCE, "RCON2365")                          # brokered deposits
    unins = _num(RCO, "RCON5597")                               # estimated uninsured
    out["DEPINS"] = out["DEP"] - unins                          # so features uninsured = unins/DEP

    out["quarter"] = quarter
    out["repdte"] = int(repdte)
    out = out.reset_index().dropna(subset=["cert"])
    out["cert"] = out["cert"].astype(int)
    return out


def build_pit_panel(periods: list[str] | None = None) -> pd.DataFrame:
    zips = sorted(RAW.glob("call_*.zip"))
    if periods:
        zips = [z for z in zips if any(p in z.name for p in periods)]
    frames = [parse_period(z) for z in zips]
    panel = pd.concat(frames, ignore_index=True)
    return panel.sort_values(["cert", "repdte"]).reset_index(drop=True)


def validate(quarter_yyyymmdd: str = "20251231") -> pd.DataFrame:
    """Reconcile parsed point-in-time fields against the FDIC panel for a recent (not-
    yet-restated) quarter. For recent quarters PIT == restated, so large diffs flag a
    mapping error."""
    from finlens_ml.train import load_dataset

    pit = parse_period(RAW / f"call_{quarter_yyyymmdd}.zip")
    q = f"{quarter_yyyymmdd[:4]}Q{_qnum(quarter_yyyymmdd)}"
    fdic = load_dataset()
    fdic = fdic[fdic["quarter"] == q]
    m = pit.merge(fdic, on="cert", suffixes=("_pit", "_fdic"))
    fields = ["ASSET", "EQ", "LNLSGR", "LNATRES", "P9LNLS", "DEP", "ROA", "ROE",
              "NIMY", "EEFFR", "NTLNLSR", "RBC1RWAJ"]
    rows = []
    for f in fields:
        a, b = f"{f}_pit", f"{f}_fdic"
        if a in m and b in m:
            pa = pd.to_numeric(m[a], errors="coerce")
            pb = pd.to_numeric(m[b], errors="coerce")
            both = pa.notna() & pb.notna()
            denom = pb[both].abs().clip(lower=1.0)
            rel = ((pa[both] - pb[both]).abs() / denom)
            rows.append({"field": f, "n": int(both.sum()),
                         "median_rel_err": round(float(rel.median()), 4),
                         "p90_rel_err": round(float(rel.quantile(0.9)), 4),
                         "frac_within_2pct": round(float((rel <= 0.02).mean()), 3)})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    import sys
    qd = sys.argv[1] if len(sys.argv) > 1 else "20251231"
    print(f"validating point-in-time parse vs FDIC for {qd}...")
    print(validate(qd).to_string(index=False))
