"""Generates a realistic fake ad-stats table (campaigns.csv): 8 campaigns x 14 days,
with a few anomalies injected into the most recent days."""
import numpy as np
import pandas as pd

rng = np.random.default_rng(7)  # fixed seed -> same data every run
DAYS = 14
CPM = 9.0

# name: (geo, daily spend $, CTR, lead rate per click, base frequency)
CAMPAIGNS = {
    "US_Fintech_Broad":     ("US", 220, 0.014, 0.12, 1.5),
    "US_Fintech_Lookalike": ("US", 180, 0.012, 0.11, 1.6),
    "UK_Loans_Video_A":     ("UK", 150, 0.016, 0.10, 1.7),
    "UK_Loans_Video_B":     ("UK", 140, 0.015, 0.096, 1.6),
    "DE_Lead_Static":       ("DE", 90, 0.010, 0.09, 1.4),
    "FR_Lead_UGC":          ("FR", 190, 0.013, 0.104, 1.5),
    "CA_Cards_Install":     ("CA", 130, 0.018, 0.08, 1.5),
    "AU_Loans_Carousel":    ("AU", 70, 0.011, 0.10, 1.4),
}

dates = pd.date_range(end=pd.Timestamp.today().normalize(), periods=DAYS)
rows = []
for name, (geo, spend0, ctr0, cr0, freq0) in CAMPAIGNS.items():
    typical_cpl = CPM / (1000 * ctr0 * cr0)
    target_cpl = round(typical_cpl * 1.10, 2)  # target is ~10% above typical CPL
    for i, d in enumerate(dates):
        days_from_end = DAYS - 1 - i  # 0 = today
        spend = spend0 * rng.normal(1.0, 0.07)
        ctr = ctr0 * rng.normal(1.0, 0.06)
        cr = cr0 * rng.normal(1.0, 0.08)
        freq = freq0 * rng.normal(1.0, 0.05)

        # ---- injected scenarios ----
        if name == "US_Fintech_Broad" and days_from_end == 0:
            cr *= 0.55                                  # CPL spike
        if name == "UK_Loans_Video_A" and days_from_end <= 2:
            ctr *= (0.5, 0.65, 0.85)[days_from_end]     # creative burning out...
            freq = (3.2, 2.9, 2.5)[days_from_end]       # ...while frequency climbs
        if name == "DE_Lead_Static" and days_from_end == 0:
            cr = 0                                      # spend, zero leads
        if name == "FR_Lead_UGC" and days_from_end <= 1:
            cr *= 1.35                                  # winner: cheap leads, low frequency

        impressions = int(spend / CPM * 1000)
        clicks = int(impressions * ctr)
        leads = int(rng.binomial(clicks, min(max(cr, 0), 1)))
        rows.append({
            "date": d.date(), "campaign_name": name, "geo": geo,
            "spend_usd": round(spend, 2), "impressions": impressions, "clicks": clicks, "leads": leads,
            "cpl_usd": round(spend / leads, 2) if leads else None,
            "target_cpl_usd": target_cpl,
            "ctr_pct": round(clicks / impressions * 100, 2),
            "frequency": round(freq, 2),
        })

pd.DataFrame(rows).to_csv("campaigns.csv", index=False)
print(f"Saved campaigns.csv: {len(rows)} rows, {len(CAMPAIGNS)} campaigns, {DAYS} days")
