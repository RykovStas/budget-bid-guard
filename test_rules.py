"""Tests for the rule logic. Run with:  python test_rules.py   (or: pytest)"""
import pandas as pd
from guard import find_alerts


def make_df(today, base=None, name="C1"):
    """7 baseline days (spend 100, 10000 imps, 150 clicks, 12 leads, freq 1.5, target 10) + a custom 'today'."""
    base_row = dict(spend_usd=100, impressions=10000, clicks=150, leads=12, frequency=1.5)
    base_row.update(base or {})
    rows = []
    for i in range(7):
        rows.append(dict(date=f"2026-01-{i+1:02d}", campaign_name=name, geo="US", target_cpl_usd=10, **base_row))
    rows.append(dict(date="2026-01-08", campaign_name=name, geo="US", target_cpl_usd=10, **today))
    return pd.DataFrame(rows)


def types(df):
    return [a["type"] for a in find_alerts(df)]


def test_normal_day_no_alerts():
    assert types(make_df(dict(spend_usd=100, impressions=10000, clicks=150, leads=11, frequency=1.5))) == []


def test_spend_no_leads():
    assert types(make_df(dict(spend_usd=100, impressions=10000, clicks=150, leads=0, frequency=1.5))) == ["SPEND_NO_LEADS"]


def test_cpl_spike():
    assert "CPL_SPIKE" in types(make_df(dict(spend_usd=150, impressions=15000, clicks=225, leads=8, frequency=1.5)))


def test_small_sample_does_not_alert():
    # CPL looks terrible (50 vs target 10) but only 2 leads: not enough data
    assert types(make_df(dict(spend_usd=100, impressions=10000, clicks=150, leads=2, frequency=1.5))) == []


def test_low_spend_ignored():
    assert types(make_df(dict(spend_usd=20, impressions=2500, clicks=40, leads=0, frequency=1.5))) == []


def test_creative_fatigue_needs_high_frequency():
    drop = dict(spend_usd=100, impressions=10000, clicks=60, leads=10, frequency=3.2)
    assert "CREATIVE_FATIGUE" in types(make_df(drop))
    drop["frequency"] = 1.5
    assert types(make_df(drop)) == ["CTR_DROP"]


def test_scale_opportunity():
    win = dict(spend_usd=200, impressions=20000, clicks=300, leads=30, frequency=1.5)  # CPL 6.7 vs target 10
    assert types(make_df(win)) == ["SCALE_OPPORTUNITY"]
    win["frequency"] = 2.6
    assert types(make_df(win)) == []  # frequency too high to scale


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok ", name)
