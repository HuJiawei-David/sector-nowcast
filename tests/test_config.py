import datetime as dt

from nowcast import config
from nowcast.quarters import Quarter

REQUIRED = {"name", "cik", "region", "revenue", "kpi", "wikipedia_articles", "volume_source",
            "exclusion_window", "headline_window", "robustness_window"}


def test_companies_complete():
    cos = config.companies()
    assert set(cos) == {"BKNG", "EXPE", "ABNB", "UBER", "LYFT", "DASH", "TCOM"}
    srcs = config.sources()
    for t, c in cos.items():
        assert REQUIRED <= set(c), t
        assert c["volume_source"] in srcs
        for a in c["wikipedia_articles"]:
            assert a["current_title"] in a["titles_since_2019"]
    assert "Ctrip" in cos["TCOM"]["wikipedia_articles"][0]["titles_since_2019"]
    assert cos["TCOM"]["kpi"] is None


def _quarter_of(effective: str) -> tuple[Quarter, int | None]:
    if "Q" in effective:
        return Quarter.parse(effective), None
    parts = [int(x) for x in effective.split("-")]
    y, m = parts[0], parts[1]
    q = Quarter(y, (m - 1) // 3 + 1)
    day_in_q = None
    if len(parts) == 3:
        start = dt.date(y, 3 * (q.q - 1) + 1, 1)
        day_in_q = (dt.date(*parts) - start).days + 1
    return q, day_in_q


def test_breaks_follow_their_rules_and_cite_sec():
    names = set(config.companies())
    for b in config.breaks():
        assert b["name"] in names
        assert b["source"].startswith("https://www.sec.gov/Archives/edgar/data/")
        aff = [Quarter.parse(q) for q in b["affected_yoy_quarters"]]
        c, day = _quarter_of(str(b["effective"]))
        rule = b["rule"]
        if rule == "c..c+4":
            assert day is None or day > 7, b["event"]
            assert aff == [c + i for i in range(5)], b["event"]
        elif rule == "c..c+3":
            assert day is not None and day <= 7, b["event"]
            assert aff == [c + i for i in range(4)], b["event"]
        elif rule == "q,q+4":
            assert aff == [c, c + 4], b["event"]
        else:
            assert rule == "explicit"
        if b.get("clean_only_note"):
            ex = config.window(config.companies()[b["name"]]["exclusion_window"])
            from nowcast.quarters import yoy_clean
            assert not any(yoy_clean(q, ex) for q in aff)


MAJOR_TYPES = {"accounting_model_change", "one_off_revenue", "kpi_definition", "business_practice_change"}


def _filing_text(url: str) -> str:
    """Whitespace-free text of a saved filing (data/raw/sec_filings/*/<NAME>_<accession>_<file>)."""
    import gzip
    import re
    from bs4 import BeautifulSoup
    parts = url.rstrip("/").split("/")
    acc, fn = parts[-2], parts[-1]
    acc = f"{acc[:10]}-{acc[10:12]}-{acc[12:]}"
    root = config.REPO_ROOT / "data" / "raw" / "sec_filings"
    hits = [p for p in root.glob(f"*/*_{acc}_{fn}*") if not p.name.endswith(".request.json")]
    assert hits, f"source filing not saved under data/raw/sec_filings: {url}"
    b = hits[0].read_bytes()
    if hits[0].suffix == ".gz":
        b = gzip.decompress(b)
    return re.sub(r"\s+", "", BeautifulSoup(b, "lxml").get_text(" "))


def test_break_materiality_follows_rule():
    import re
    for b in config.breaks():
        m, typ = b["materiality"], b["type"]
        assert m in {"major", "minor"}, b["event"]
        quote = b.get("materiality_quote")
        if typ in MAJOR_TYPES:
            assert m == "major" and b["materiality_basis"].startswith("(a)"), b["event"]
        elif m == "major":  # only via rule (b): a verbatim sentence from a saved filing
            assert b["materiality_basis"].startswith("(b)") and quote, b["event"]
            assert re.sub(r"\s+", "", quote) in _filing_text(b["materiality_source"]), b["event"]
        else:
            assert quote is None and b["materiality_basis"].startswith("neither"), b["event"]
