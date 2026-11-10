-- Sector Nowcast schema (Session 2). Portable SQL: runs on SQLite and PostgreSQL unchanged.
-- Dates are ISO-8601 strings in DATE columns ('YYYY-MM-DD'); quarters are 'YYYYQn' labels.
-- Every revenue/KPI number keeps its filing (accession), filing date and source URL, so the
-- point-in-time rule (filed < asof) can be applied in SQL as well as in Python.

DROP TABLE IF EXISTS reconciliation;
DROP TABLE IF EXISTS release_values;
DROP TABLE IF EXISTS revenue_versions;
DROP TABLE IF EXISTS earnings_releases;
DROP TABLE IF EXISTS companies;

CREATE TABLE companies (
    name            VARCHAR(8)   PRIMARY KEY,
    legal_name      VARCHAR(100) NOT NULL,
    cik             INTEGER      NOT NULL,
    region          VARCHAR(8)   NOT NULL,
    revenue_source  VARCHAR(20)  NOT NULL,
    currency        VARCHAR(3)   NOT NULL,
    kpi_name        VARCHAR(60)
);

-- One row per earnings release (8-K Item 2.02 Ex-99.1, or 6-K results Ex-99.1); amendments kept.
CREATE TABLE earnings_releases (
    name            VARCHAR(8)   NOT NULL REFERENCES companies(name),
    quarter         VARCHAR(6)   NOT NULL,
    filed           DATE         NOT NULL,
    accession       VARCHAR(20)  NOT NULL,
    form            VARCHAR(8)   NOT NULL,
    is_amendment    INTEGER      NOT NULL,
    document        VARCHAR(120) NOT NULL,
    source_url      VARCHAR(300) NOT NULL,
    PRIMARY KEY (name, accession)
);

-- Every filed version of quarterly revenue (XBRL for US names, 6-K releases for TCOM).
CREATE TABLE revenue_versions (
    name            VARCHAR(8)   NOT NULL REFERENCES companies(name),
    quarter         VARCHAR(6)   NOT NULL,
    value           NUMERIC      NOT NULL,      -- millions of `currency`
    unit            VARCHAR(20)  NOT NULL,
    currency        VARCHAR(3)   NOT NULL,
    period_start    DATE,
    period_end      DATE,
    fy              INTEGER,
    fp              VARCHAR(4),
    form            VARCHAR(10)  NOT NULL,
    filed           DATE         NOT NULL,
    accession       VARCHAR(20)  NOT NULL,
    tag             VARCHAR(80),
    method          VARCHAR(20)  NOT NULL,      -- reported_3m | derived_ytd | press_release
    derivation      VARCHAR(300),
    source_url      VARCHAR(300) NOT NULL,
    PRIMARY KEY (name, quarter, accession)
);

-- Every number read from an earnings release: KPI and revenue levels, and stated Y/Y %.
CREATE TABLE release_values (
    name            VARCHAR(8)   NOT NULL REFERENCES companies(name),
    metric          VARCHAR(10)  NOT NULL,      -- kpi | revenue
    kind            VARCHAR(20)  NOT NULL,      -- value | stated_yoy_pct
    quarter         VARCHAR(6)   NOT NULL,      -- period the number refers to
    value           NUMERIC      NOT NULL,
    unit            VARCHAR(20),
    decimals        INTEGER      NOT NULL,
    value_precision NUMERIC      NOT NULL,      -- one unit of the last disclosed digit
    role            VARCHAR(30)  NOT NULL,      -- current | prior_year_comparative | other_period
    release_quarter VARCHAR(6)   NOT NULL,
    filed           DATE         NOT NULL,
    accession       VARCHAR(20)  NOT NULL,
    form            VARCHAR(8)   NOT NULL,
    extractors      VARCHAR(300) NOT NULL,
    source_url      VARCHAR(300) NOT NULL,
    PRIMARY KEY (name, metric, kind, quarter, accession)
);

CREATE TABLE reconciliation (
    name            VARCHAR(8)   NOT NULL,
    quarter         VARCHAR(6)   NOT NULL,
    check_name      VARCHAR(40)  NOT NULL,
    ours            NUMERIC,
    company         NUMERIC,
    company_basis   VARCHAR(200),
    diff            NUMERIC,
    tolerance       NUMERIC,
    status          VARCHAR(300) NOT NULL,
    source_url      VARCHAR(300),
    PRIMARY KEY (name, quarter, check_name)
);
