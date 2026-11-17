-- Per-cell evaluation results (outputs/tables/results.csv + robustness.csv), loaded by
-- evaluate.results_db() (Sessions 4-5). Portable SQL (SQLite and PostgreSQL).
DROP TABLE IF EXISTS results_cells;

CREATE TABLE results_cells (
    analysis              VARCHAR(80)  NOT NULL,   -- headline | robustness (i)/(ii)/(iii) ...
    name_order            INTEGER      NOT NULL,   -- config/companies.yaml order
    name                  VARCHAR(8)   NOT NULL,
    source                VARCHAR(12)  NOT NULL,   -- tsa | caac | hkia | wikipedia | combined
    target                VARCHAR(1)   NOT NULL,   -- y | k
    model                 VARCHAR(10)  NOT NULL,   -- direction | magnitude
    status                VARCHAR(200) NOT NULL,
    family_member         INTEGER      NOT NULL,
    n_prereg              INTEGER,
    n_realised            INTEGER      NOT NULL,
    hits                  INTEGER,
    min_hits_p05          INTEGER,
    momentum_hits         INTEGER,
    beats_both            INTEGER,
    binom_p               NUMERIC,
    bh_q_binom            NUMERIC,
    mae_pp                NUMERIC,
    mae_baseline_pp       NUMERIC,
    placebo_percentile    NUMERIC,                 -- shuffle placebo (Session 5)
    bh_q_placebo          NUMERIC,
    green                 INTEGER,                 -- beats both baselines AND placebo percentile >= 95
    PRIMARY KEY (analysis, name, source, target, model)
);
