"""Session 2: pull SEC raw snapshots (hard rule 8). Run from repo root:

    .venv/bin/python scripts/s2_pull_sec.py

1. submissions (incl. older pages) for all 7 names            -> data/raw/sec_submissions/<today>/
2. XBRL companyfacts for all 7 names (TCOM only for the 20-F FY check) -> data/raw/sec_companyfacts/<today>/
3. US: every 8-K / 8-K/A with Item 2.02 filed since `releases_since`: filing index + EX-99.1
   TCOM: every 6-K filed since `releases_since`: filing index + primary document; EX-99.1 of the
   results releases                                            -> data/raw/sec_filings/<today>/
The User-Agent comes only from SEC_USER_AGENT / .env (src/nowcast/sec.py); it is never printed.
Re-runs on the same day reuse what was already saved (sec.fetch_once).
"""
import datetime as dt
import json
import re
import sys

sys.path.insert(0, "src")
from nowcast import config, filings, sec  # noqa: E402

TODAY = dt.date.today().isoformat()
PIPE = config.load_yaml("pipeline.yaml")
SINCE = dt.date.fromisoformat(PIPE["releases_since"])
TCOM_RESULTS_RE = re.compile(PIPE["tcom_results_release_regex"], re.I)


def pull_submissions(t, cik):
    body, _ = sec.fetch_once(sec.submissions_url(cik), "sec_submissions", f"{t}_CIK{cik:010d}.json", TODAY,
                             ticker=t, cik=cik)
    for f in json.loads(body)["filings"].get("files", []):
        sec.fetch_once(sec.submissions_page_url(f["name"]), "sec_submissions", f"{t}_{f['name']}", TODAY,
                       ticker=t, cik=cik)


def pull_index(t, cik, acc):
    body, _ = sec.fetch_once(sec.filing_index_url(cik, acc), "sec_filings", f"{t}_{acc}_index.htm", TODAY,
                             ticker=t, accession=acc)
    return filings.parse_index(body)


def pull_doc(t, cik, acc, doc):
    return sec.fetch_once(filings.doc_url(cik, acc, doc), "sec_filings", f"{t}_{acc}_{doc}", TODAY,
                          compress=True, ticker=t, accession=acc, document=doc)


def main():
    cos = config.companies()
    for t, c in cos.items():
        cik = c["cik"]
        pull_submissions(t, cik)
        sec.fetch_once(sec.companyfacts_url(cik), "sec_companyfacts", f"{t}_CIK{cik:010d}.json", TODAY,
                       compress=True, ticker=t, cik=cik)
        sub = filings.submissions(t, cik, TODAY)
        if c["region"] == "US":
            er = filings.earnings_8k(sub, SINCE)
            for _, r in er.iterrows():
                idx = pull_index(t, cik, r.accessionNumber)
                ex = filings.exhibit_991(idx)
                if ex is None:
                    print(f"  {t} {r.accessionNumber} {r.filingDate}: no EX-99.1 (form {r.form})")
                    continue
                pull_doc(t, cik, r.accessionNumber, ex)
            print(f"{t}: {len(er)} Item 2.02 8-K(s) since {SINCE}")
        else:
            six = sub[(sub["form"] == "6-K") & (sub["filingDate"] >= SINCE)]
            n_res = 0
            for _, r in six.iterrows():
                idx = pull_index(t, cik, r.accessionNumber)
                prim, _ = pull_doc(t, cik, r.accessionNumber, r.primaryDocument)
                if not TCOM_RESULTS_RE.search(filings.html_to_text(prim)):
                    continue
                ex = filings.exhibit_991(idx)
                if ex is None:
                    raise RuntimeError(f"TCOM results 6-K {r.accessionNumber} has no EX-99.1")
                pull_doc(t, cik, r.accessionNumber, ex)
                n_res += 1
            print(f"{t}: {len(six)} 6-K(s) since {SINCE}, {n_res} results release(s)")


if __name__ == "__main__":
    main()
