"""Deterministic synthetic generator for the Bank Model-Risk Knowledge Graph.

Produces a realistic-but-synthetic model-risk inventory for a mid-size bank:
models, the data + features they consume, the assumptions they make, their
validations and findings, the regulations that govern them, the controls that
satisfy those regulations, the people accountable, the business units, the
regulatory submissions they feed, and the decisions they drive.

No external data, no PII, no real institution — everything is generated from a
fixed seed so the graph (and its snapshot hash) is reproducible. The shape is
chosen so the governance questions in ../queries/governance-queries.cypher all
return meaningful rows: lineage / blast-radius, regulatory coverage, open
high-severity findings, single-points-of-failure, and model explainability.

Returns
-------
nodes : list[(label, props_dict)]            # props always include a unique "id"
edges : list[(src_label, src_id, rel, tgt_label, tgt_id, props_or_None)]
"""
from __future__ import annotations

import random

SEED = 42

# --- vocab ----------------------------------------------------------------
BUSINESS_UNITS = [
    "Retail Credit", "Wholesale Credit", "Cards & Unsecured", "Markets",
    "Treasury & ALM", "Financial Crime", "Capital Management", "Model Risk",
]

# (category, regulatory_use, typical_tier_bias)
MODEL_CATEGORIES = [
    ("PD — Probability of Default", True, 1),
    ("LGD — Loss Given Default", True, 1),
    ("EAD — Exposure at Default", True, 2),
    ("IFRS9 ECL", True, 1),
    ("CCAR PPNR", True, 1),
    ("CCAR Loss Projection", True, 1),
    ("Credit Scorecard", True, 2),
    ("AML Transaction Monitoring", True, 1),
    ("Fraud Detection", True, 2),
    ("Market Risk VaR", True, 2),
    ("Liquidity Stress", True, 2),
    ("LLM Adverse-Media Screening", True, 1),
    ("Customer Churn", False, 3),
    ("Next-Best-Product", False, 3),
]

PORTFOLIOS = [
    "Large Corporate", "SME", "Retail Mortgage", "Auto", "Credit Card",
    "Unsecured Personal", "Commercial Real Estate", "Project Finance",
    "Sovereign", "Financial Institutions",
]

DATA_SOURCES = [
    ("Core Banking Ledger", "Internal", "GL System", "Confidential", "Daily"),
    ("Loan Origination System", "Internal", "LOS", "Confidential", "Daily"),
    ("Credit Bureau Feed", "Vendor", "Bureau API", "Restricted", "Weekly"),
    ("Macroeconomic Scenarios", "Regulatory", "Fed/ECB CCAR", "Public", "Quarterly"),
    ("Market Data Feed", "Vendor", "Bloomberg", "Internal", "Realtime"),
    ("Transaction Monitoring Store", "Internal", "AML Hub", "Restricted", "Realtime"),
    ("KYC / Customer Master", "Internal", "CRM", "Restricted", "Daily"),
    ("Collateral Register", "Internal", "Collateral DB", "Confidential", "Daily"),
    ("Payments Switch Log", "Internal", "Payments", "Confidential", "Realtime"),
    ("Sanctions & Watchlists", "External", "OFAC/UN", "Public", "Daily"),
    ("Adverse Media Corpus", "Vendor", "News API", "Internal", "Daily"),
    ("Treasury Positions", "Internal", "TMS", "Confidential", "Daily"),
    ("Deposits Behavioural Store", "Internal", "Deposits", "Confidential", "Daily"),
    ("Vendor Macro Forecasts", "Vendor", "Moody's", "Internal", "Quarterly"),
    ("Internal Ratings Repository", "Internal", "Rating Engine", "Confidential", "Daily"),
]

FEATURES = [
    ("debt_to_income", "float", False), ("loan_to_value", "float", False),
    ("delinquency_30d_count", "int", False), ("utilisation_ratio", "float", False),
    ("months_on_book", "int", False), ("bureau_score", "int", True),
    ("gdp_growth", "float", False), ("unemployment_rate", "float", False),
    ("hpi_change", "float", False), ("interest_rate_shock", "float", False),
    ("avg_balance_volatility", "float", False), ("counterparty_exposure", "float", False),
    ("txn_velocity_24h", "float", True), ("cross_border_ratio", "float", True),
    ("cash_intensity", "float", True), ("watchlist_hit", "int", True),
    ("adverse_media_score", "float", True), ("collateral_coverage", "float", False),
    ("rating_migration", "float", False), ("deposit_runoff_rate", "float", False),
    ("vintage_quality", "float", False), ("region_concentration", "float", False),
    ("sector_concentration", "float", False), ("recovery_rate", "float", False),
]

ASSUMPTIONS = [
    ("Macro path follows supervisory severely-adverse scenario", "Macro"),
    ("Default behaviour stationary across the cycle", "Behavioral"),
    ("Recovery lag of 18 months on secured exposures", "Behavioral"),
    ("Log-normal distribution of portfolio losses", "Statistical"),
    ("No structural break in delinquency roll-rates", "Statistical"),
    ("Collateral values revalued quarterly", "Operational"),
    ("LLM screening recall calibrated on 2024 backbook", "Behavioral"),
    ("Deposit beta constant under rate shocks", "Behavioral"),
    ("Independence of obligor defaults within rating grade", "Statistical"),
    ("Sanctions list completeness within 24h SLA", "Operational"),
    ("Bureau score predictive power stable YoY", "Statistical"),
    ("Severely-adverse unemployment peak of 10%", "Macro"),
]

REG_REQS = [
    ("SR 11-7", "II", "Model development, implementation and use evidenced"),
    ("SR 11-7", "III", "Independent model validation with effective challenge"),
    ("SR 11-7", "IV", "Model inventory and governance with clear ownership"),
    ("Basel III", "CRE36", "IRB models: rating system design and quantification"),
    ("Basel III", "MAR", "Market risk internal models approval"),
    ("IFRS 9", "5.5", "Expected credit loss measurement and staging"),
    ("IFRS 9", "B5.5", "Forward-looking information and scenarios"),
    ("ECB TRIM", "GIM", "General topics: model governance and data quality"),
    ("ECB TRIM", "Credit", "Credit risk: PD/LGD estimation soundness"),
    ("EU AI Act", "Art.9", "High-risk AI: risk management system"),
    ("EU AI Act", "Art.13", "High-risk AI: transparency and explainability"),
    ("EU AI Act", "Art.14", "High-risk AI: human oversight"),
    ("RBI", "MRM", "Model risk management framework for banks"),
    ("CCAR/DFAST", "Stress", "Capital stress-test model governance"),
    ("BCBS 239", "P3", "Risk data aggregation: accuracy and integrity"),
    ("FRTB", "IMA", "Internal models approach eligibility"),
]

CONTROLS = [
    ("Annual independent validation", "Governance", "Annual"),
    ("Ongoing performance monitoring", "Detective", "Monthly"),
    ("Benchmarking against challenger model", "Detective", "Quarterly"),
    ("Backtesting of risk estimates", "Detective", "Quarterly"),
    ("Data quality reconciliation", "Preventive", "Daily"),
    ("Override logging and review", "Detective", "Monthly"),
    ("Model change approval gate", "Preventive", "Per-change"),
    ("Assumption review board", "Governance", "Semi-annual"),
    ("Explainability / reason-code review", "Detective", "Quarterly"),
    ("Human-in-the-loop sign-off", "Preventive", "Per-decision"),
    ("Bias & fairness testing", "Detective", "Annual"),
    ("Sanctions screening QA", "Detective", "Daily"),
]

SUBMISSIONS = [
    ("CCAR 2026", "Federal Reserve", "Annual", "2026-04-05"),
    ("DFAST 2026", "Federal Reserve", "Annual", "2026-04-05"),
    ("IFRS9 ECL Q2 2026", "External Audit", "Quarterly", "2026-07-15"),
    ("ICAAP 2026", "ECB / Local Regulator", "Annual", "2026-09-30"),
    ("AML SAR Program", "FinCEN / FIU", "Continuous", "2026-12-31"),
    ("Pillar 3 Disclosure 2026", "Regulator (Public)", "Annual", "2026-03-31"),
]

DECISIONS = [
    ("Credit Approval — Wholesale", "Credit Approval"),
    ("Credit Approval — Retail", "Credit Approval"),
    ("Counterparty Limit Setting", "Limit Setting"),
    ("ECL Provisioning", "Provisioning"),
    ("Capital Allocation", "Capital Allocation"),
    ("AML Alert Disposition", "Alert Disposition"),
    ("Fraud Block / Step-up", "Alert Disposition"),
    ("Pricing & Risk Appetite", "Pricing"),
    ("Trading Limit Utilisation", "Limit Setting"),
    ("Onboarding Risk Rating", "Onboarding"),
]

ROLES = ["Model Owner", "Model Validator", "Model Risk Officer", "Developer", "CRO"]
FIRST = ["Aarav", "Diya", "Kabir", "Mei", "Sofia", "Liam", "Noor", "Ravi", "Elena",
         "Omar", "Hana", "Tomas", "Ines", "Yuki", "Diganta", "Lina", "Marco",
         "Sara", "Wei", "Priya", "Jonas", "Amara", "Felix", "Nadia", "Carlos"]
LAST = ["Sharma", "Khan", "Okafor", "Tan", "Rossi", "Nguyen", "Haddad", "Iyer",
        "Petrov", "Silva", "Cohen", "Dubois", "Costa", "Yamada", "Saikia",
        "Mwangi", "Larsen", "Park", "Reyes", "Schmidt"]

OUTCOMES = ["Pass", "Pass with conditions", "Fail"]
VAL_TYPES = ["Initial validation", "Annual validation", "Ongoing monitoring"]
SEVERITIES = ["High", "Medium", "Low"]
FINDING_CATS = ["Data", "Methodology", "Implementation", "Documentation", "Performance"]
FINDING_TITLES = {
    "Data": ["Stale reference data", "Unreconciled feed", "Missing lineage", "Outlier handling gap"],
    "Methodology": ["Unjustified assumption", "Weak segmentation", "Overfitting risk", "Calibration drift"],
    "Implementation": ["Code/spec mismatch", "Rounding error", "Untested edge case", "Env config gap"],
    "Documentation": ["Incomplete model doc", "No effective-challenge record", "Stale assumption log"],
    "Performance": ["Discriminatory power decline", "Backtest breach", "PSI above threshold", "Bias metric breach"],
}


def generate():
    rng = random.Random(SEED)
    nodes: list[tuple[str, dict]] = []
    edges: list[tuple] = []

    def add_node(label, _id, **props):
        props["id"] = _id
        nodes.append((label, props))
        return _id

    def add_edge(sl, sid, rel, tl, tid, props=None):
        edges.append((sl, sid, rel, tl, tid, props))

    # --- business units ---
    bu_ids = []
    for i, name in enumerate(BUSINESS_UNITS):
        bu_ids.append(add_node("BusinessUnit", f"BU{i:02d}", name=name))

    # --- people ---
    person_ids = []
    used = set()
    for i in range(28):
        while True:
            nm = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
            if nm not in used:
                used.add(nm)
                break
        role = ROLES[i % len(ROLES)] if i < len(ROLES) else rng.choice(ROLES)
        bu = rng.choice(bu_ids)
        pid = add_node("Person", f"P{i:03d}", name=nm, role=role)
        add_edge("Person", pid, "MEMBER_OF", "BusinessUnit", bu)
        person_ids.append((pid, role))
    owners = [p for p, r in person_ids if r in ("Model Owner", "Model Risk Officer", "CRO")]
    validators = [p for p, r in person_ids if r in ("Model Validator", "Model Risk Officer")]
    developers = [p for p, r in person_ids if r in ("Developer", "Model Owner")]

    # --- data sources ---
    ds_ids = {}
    for i, (name, typ, system, sens, refresh) in enumerate(DATA_SOURCES):
        ds_ids[name] = add_node("DataSource", f"DS{i:02d}", name=name, type=typ,
                                system=system, sensitivity=sens, refresh=refresh)

    # --- features (each derived from 1 data source) ---
    feat_ids = []
    for i, (name, dtype, pii) in enumerate(FEATURES):
        fid = add_node("Feature", f"F{i:03d}", name=name, data_type=dtype, pii=(1 if pii else 0))
        src = rng.choice(list(ds_ids.values()))
        add_edge("Feature", fid, "DERIVED_FROM", "DataSource", src)
        feat_ids.append(fid)

    # --- assumptions ---
    assum_ids = []
    for i, (desc, cat) in enumerate(ASSUMPTIONS):
        status = rng.choices(["Valid", "Stale", "Breached"], weights=[6, 3, 1])[0]
        assum_ids.append(add_node("Assumption", f"A{i:03d}", description=desc,
                                  category=cat, status=status))

    # --- regulatory requirements ---
    reg_ids = []
    for i, (fw, clause, title) in enumerate(REG_REQS):
        reg_ids.append(add_node("RegulatoryRequirement", f"R{i:03d}", framework=fw,
                                clause=clause, title=title))
    sr117 = [r for (r, (fw, *_)) in zip(reg_ids, REG_REQS) if fw == "SR 11-7"]
    ai_act = [r for (r, (fw, *_)) in zip(reg_ids, REG_REQS) if fw == "EU AI Act"]

    # --- controls (each satisfies 1-2 requirements) ---
    ctrl_ids = []
    for i, (name, ctype, freq) in enumerate(CONTROLS):
        status = rng.choices(["Effective", "Needs improvement", "Not tested"],
                             weights=[6, 3, 1])[0]
        cid = add_node("Control", f"C{i:03d}", name=name, type=ctype,
                       frequency=freq, status=status)
        for r in rng.sample(reg_ids, rng.randint(1, 2)):
            add_edge("Control", cid, "SATISFIES", "RegulatoryRequirement", r)
        ctrl_ids.append(cid)

    # --- submissions ---
    sub_ids = {}
    for i, (name, reg, freq, due) in enumerate(SUBMISSIONS):
        sub_ids[name] = add_node("Submission", f"S{i:02d}", name=name, regulator=reg,
                                 frequency=freq, next_due=due)

    # --- decisions ---
    dec_ids = []
    for i, (name, dtype) in enumerate(DECISIONS):
        dec_ids.append(add_node("Decision", f"D{i:02d}", name=name, type=dtype))

    # --- models (the centre of gravity) ---
    NUM_MODELS = 80
    model_ids = []
    feeder_models = []   # PD/LGD/EAD/scorecard etc that feed aggregate models
    aggregate_models = {}  # category -> model id (CCAR/IFRS9 that consume feeders)

    for i in range(NUM_MODELS):
        cat, reg_use, tier_bias = rng.choice(MODEL_CATEGORIES)
        portfolio = rng.choice(PORTFOLIOS)
        name = f"{cat.split(' — ')[0].split(' ')[0]}-{portfolio}-{i:03d}"
        name = f"{cat.split(' —')[0]} · {portfolio}"
        # de-dupe-ish: append index for uniqueness
        name = f"{cat.split(' —')[0]} · {portfolio} #{i:02d}"
        tier = min(3, max(1, tier_bias + rng.choice([-0, 0, 0, 1])))
        status = rng.choices(["Production", "Development", "Retired"],
                             weights=[7, 2, 1])[0]
        methodology = rng.choice(["Logistic regression", "Gradient boosting",
                                  "Survival model", "Monte Carlo", "Rules + ML",
                                  "Transformer LLM", "Hybrid econometric"])
        mid = add_node("Model", f"M{i:03d}", name=name, category=cat, tier=tier,
                       status=status, regulatory_use=(1 if reg_use else 0),
                       methodology=methodology,
                       last_validated=f"202{rng.randint(4,6)}-{rng.randint(1,12):02d}-15")
        model_ids.append((mid, cat, tier, status, reg_use))

        # ownership / dev / unit
        add_edge("Model", mid, "OWNED_BY", "Person", rng.choice(owners))
        add_edge("Model", mid, "DEVELOPED_BY", "Person", rng.choice(developers))
        add_edge("Model", mid, "BELONGS_TO", "BusinessUnit", rng.choice(bu_ids))

        # data sources: 2-4, with a strong bias to Core Banking Ledger (concentration)
        ds_choice = set(rng.sample(list(ds_ids.values()), rng.randint(2, 4)))
        if rng.random() < 0.55:
            ds_choice.add(ds_ids["Core Banking Ledger"])
        for ds in ds_choice:
            add_edge("Model", mid, "DEPENDS_ON", "DataSource", ds)

        # features: 3-6
        for f in rng.sample(feat_ids, rng.randint(3, 6)):
            add_edge("Model", mid, "USES_FEATURE", "Feature", f)

        # assumptions: 1-3
        for a in rng.sample(assum_ids, rng.randint(1, 3)):
            add_edge("Model", mid, "MAKES_ASSUMPTION", "Assumption", a)

        # governance: regulatory requirements. All reg-use models -> SR 11-7 core.
        govs = set()
        if reg_use:
            govs.update(rng.sample(sr117, k=min(2, len(sr117))))
            govs.add(rng.choice(reg_ids))
        if "LLM" in cat:
            govs.update(ai_act)
        for g in govs:
            add_edge("Model", mid, "GOVERNED_BY", "RegulatoryRequirement", g)

        # controls applied: 2-4
        for c in rng.sample(ctrl_ids, rng.randint(2, 4)):
            add_edge("Model", mid, "CONTROLLED_BY", "Control", c)

        # decisions: production models drive 1-2 decisions
        if status == "Production":
            for d in rng.sample(dec_ids, rng.randint(1, 2)):
                add_edge("Model", mid, "USED_IN", "Decision", d)

        # classify feeders vs aggregates
        if cat in ("CCAR Loss Projection", "CCAR PPNR", "IFRS9 ECL"):
            aggregate_models.setdefault(cat, []).append(mid)
        elif cat.startswith(("PD", "LGD", "EAD", "Credit Scorecard", "Market Risk")):
            feeder_models.append(mid)

    # --- model -> model FEEDS (upstream risk params feed stress/ECL engines) ---
    for cat, aggs in aggregate_models.items():
        for agg in aggs:
            for feeder in rng.sample(feeder_models, k=min(len(feeder_models), rng.randint(2, 4))):
                add_edge("Model", feeder, "FEEDS", "Model", agg)

    # --- model -> submission FEEDS ---
    def feed_sub(cat_keys, sub_name):
        for mid, cat, tier, status, reg_use in model_ids:
            if any(k in cat for k in cat_keys) and status != "Retired":
                add_edge("Model", mid, "FEEDS", "Submission", sub_ids[sub_name])

    feed_sub(["CCAR"], "CCAR 2026")
    feed_sub(["CCAR", "Market Risk", "Liquidity"], "DFAST 2026")
    feed_sub(["IFRS9"], "IFRS9 ECL Q2 2026")
    feed_sub(["PD", "LGD", "EAD", "CCAR", "Market Risk", "Liquidity"], "ICAAP 2026")
    feed_sub(["AML", "Fraud", "LLM"], "AML SAR Program")
    feed_sub(["PD", "LGD", "IFRS9", "Market Risk"], "Pillar 3 Disclosure 2026")

    # Ensure feeders also reach CCAR submission through the aggregate chain already.

    # --- validations + findings ---
    vcount = 0
    fcount = 0
    for mid, cat, tier, status, reg_use in model_ids:
        if status == "Retired":
            n_val = rng.randint(0, 1)
        else:
            n_val = rng.randint(1, 2) if tier >= 3 else rng.randint(1, 3)
        for _ in range(n_val):
            # higher-tier models skew to having conditions/fails open
            if tier == 1:
                outcome = rng.choices(OUTCOMES, weights=[4, 4, 2])[0]
            elif tier == 2:
                outcome = rng.choices(OUTCOMES, weights=[6, 3, 1])[0]
            else:
                outcome = rng.choices(OUTCOMES, weights=[8, 2, 0])[0]
            vid = add_node("Validation", f"V{vcount:04d}", outcome=outcome,
                           type=rng.choice(VAL_TYPES),
                           date=f"202{rng.randint(4,6)}-{rng.randint(1,12):02d}-{rng.randint(1,28):02d}")
            vcount += 1
            add_edge("Model", mid, "VALIDATED_BY", "Validation", vid)
            add_edge("Validation", vid, "PERFORMED_BY", "Person", rng.choice(validators))
            # the validation evidences one of the model's controls
            add_edge("Validation", vid, "EVIDENCES", "Control", rng.choice(ctrl_ids))

            # findings: failures/conditions raise more, higher severity
            if outcome == "Fail":
                n_find = rng.randint(2, 4)
                sev_w = [6, 3, 1]
            elif outcome == "Pass with conditions":
                n_find = rng.randint(1, 3)
                sev_w = [3, 5, 2]
            else:
                n_find = rng.randint(0, 1)
                sev_w = [1, 3, 6]
            for _ in range(n_find):
                cat_f = rng.choice(FINDING_CATS)
                sev = rng.choices(SEVERITIES, weights=sev_w)[0]
                # Tier-1 production models keep some High findings OPEN (governance gap)
                if sev == "High":
                    fstatus = rng.choices(["Open", "Overdue", "Closed"], weights=[4, 2, 4])[0]
                else:
                    fstatus = rng.choices(["Open", "Overdue", "Closed"], weights=[3, 1, 6])[0]
                fid = add_node("ValidationFinding", f"VF{fcount:04d}",
                               title=rng.choice(FINDING_TITLES[cat_f]),
                               category=cat_f, severity=sev, status=fstatus,
                               raised_date=f"202{rng.randint(5,6)}-{rng.randint(1,12):02d}-10")
                fcount += 1
                add_edge("Validation", vid, "RAISED", "ValidationFinding", fid)

    return nodes, edges


if __name__ == "__main__":
    n, e = generate()
    from collections import Counter
    print(f"nodes: {len(n)}  edges: {len(e)}")
    print("by label:", dict(Counter(l for l, _ in n)))
    print("by rel:  ", dict(Counter(t[2] for t in e)))
