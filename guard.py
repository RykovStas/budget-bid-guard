"""Budget & Bid Guard.

1. Rule-based checks (plain Python) compare the latest day to the previous 7 days and to each
   campaign's target CPL, and flag anomalies and scaling opportunities.
2. An LLM (OpenAI or Gemini) turns the flagged items into a short, readable Slack alert.
3. The alert is posted to Slack through an Incoming Webhook.

The LLM never makes decisions: every flag and diagnosis comes from the rules below,
and its recommendations are for a human media buyer to review.
"""
import json
import os
import sys

import pandas as pd
import requests
import time


def post_with_retry(url, retries=3, **kwargs):
    """Retry on temporary errors (429, 500, 503) with growing pauses."""
    for attempt in range(retries + 1):
        r = requests.post(url, **kwargs)
        if r.status_code not in (429, 500, 503) or attempt == retries:
            r.raise_for_status()
            return r
        wait = 2 ** attempt * 2  # 2, 4, 8 seconds
        print(f"Temporary error {r.status_code}, retrying in {wait}s...")
        time.sleep(wait)


def load_env(path=".env"):
    """Tiny .env reader so no extra package is needed."""
    if not os.path.exists(path):
        return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


load_env()


def cfg(name, default):
    return float(os.getenv(name, default))


MIN_SPEND = cfg("MIN_SPEND", 50)                      # ignore campaigns with less spend today
MIN_LEADS = cfg("MIN_LEADS", 5)                       # minimum sample for CPL-based rules
MIN_IMPRESSIONS = cfg("MIN_IMPRESSIONS", 2000)        # minimum sample for CTR rule
CPL_OVER_TARGET_PCT = cfg("CPL_OVER_TARGET_PCT", 25)  # CPL this % above target -> alert
CTR_DROP_PCT = cfg("CTR_DROP_PCT", 30)                # CTR this % below baseline -> alert
FREQ_FATIGUE = cfg("FREQ_FATIGUE", 2.8)               # CTR drop + frequency above this = fatigue
SCALE_MIN_SPEND = cfg("SCALE_MIN_SPEND", 150)
SCALE_UNDER_TARGET_PCT = cfg("SCALE_UNDER_TARGET_PCT", 15)
SCALE_MAX_FREQ = cfg("SCALE_MAX_FREQ", 2.0)
BASELINE_DAYS = 7

SEVERITY = {"SPEND_NO_LEADS": 0, "CPL_SPIKE": 1, "CREATIVE_FATIGUE": 2, "CTR_DROP": 3, "SCALE_OPPORTUNITY": 4}


def find_alerts(df):
    """Return a list of flagged campaigns (dicts) for the latest date in df."""
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    last_day = df["date"].max()
    today_df = df[df["date"] == last_day]
    base_df = df[(df["date"] < last_day) & (df["date"] >= last_day - pd.Timedelta(days=BASELINE_DAYS))]

    alerts = []
    for _, t in today_df.iterrows():
        name = t["campaign_name"]
        b = base_df[base_df["campaign_name"] == name]
        if b.empty:
            continue

        spend, leads = float(t["spend_usd"]), int(t["leads"])
        imps, clicks = int(t["impressions"]), int(t["clicks"])
        freq, target = float(t["frequency"]), float(t["target_cpl_usd"])
        cpl = spend / leads if leads else None
        ctr = clicks / imps * 100 if imps else 0.0

        b_leads = int(b["leads"].sum())
        b_cpl = b["spend_usd"].sum() / b_leads if b_leads else None
        b_ctr = b["clicks"].sum() / b["impressions"].sum() * 100
        b_freq = float(b["frequency"].mean())

        def alert(kind, note, **extra):
            alerts.append({
                "campaign": name, "geo": t["geo"], "type": kind, "note": note,
                "spend_usd": round(spend, 2), "leads": leads,
                "cpl_usd": round(cpl, 2) if cpl else None, "target_cpl_usd": round(target, 2),
                "ctr_pct": round(ctr, 2), "frequency": round(freq, 2),
                "baseline_cpl_usd": round(b_cpl, 2) if b_cpl else None,
                "baseline_ctr_pct": round(b_ctr, 2), "baseline_frequency": round(b_freq, 2),
                **extra,
            })

        if spend < MIN_SPEND:
            continue  # not enough spend to say anything

        # 1) Spend with zero leads, while the baseline produced leads
        if leads == 0 and b_leads > 0:
            alert("SPEND_NO_LEADS", "Spend today with zero leads; baseline had leads (check tracking, landing page, ad status).")
            continue

        # 2) CPL well above target (with a minimum lead sample to avoid noise)
        if leads >= MIN_LEADS and cpl >= target * (1 + CPL_OVER_TARGET_PCT / 100):
            alert("CPL_SPIKE", f"CPL is {(cpl / target - 1) * 100:.0f}% above target.",
                  over_target_pct=round((cpl / target - 1) * 100, 1))

        # 3) CTR drop vs baseline; with high frequency it points to creative fatigue
        if imps >= MIN_IMPRESSIONS and b_ctr > 0:
            change = (ctr / b_ctr - 1) * 100
            if change <= -CTR_DROP_PCT:
                if freq >= FREQ_FATIGUE:
                    alert("CREATIVE_FATIGUE", f"CTR down {abs(change):.0f}% vs 7-day baseline while frequency is {freq:.1f}: likely creative fatigue.",
                          ctr_change_pct=round(change, 1))
                else:
                    alert("CTR_DROP", f"CTR down {abs(change):.0f}% vs 7-day baseline, frequency still low ({freq:.1f}): not fatigue, check creative/audience/placement changes.",
                          ctr_change_pct=round(change, 1))

        # 4) Scaling opportunity: cheap leads today AND over the baseline, low frequency
        if (spend >= SCALE_MIN_SPEND and leads >= MIN_LEADS and freq < SCALE_MAX_FREQ
                and cpl <= target * (1 - SCALE_UNDER_TARGET_PCT / 100)
                and b_cpl is not None and b_cpl <= target):
            alert("SCALE_OPPORTUNITY", f"CPL {(1 - cpl / target) * 100:.0f}% under target, baseline also within target, frequency {freq:.1f}.",
                  under_target_pct=round((1 - cpl / target) * 100, 1))

    alerts.sort(key=lambda a: SEVERITY[a["type"]])
    return alerts


PROMPT = """You are a Senior Performance Marketing Analyst at a European FinTech company.
Below are Meta Ads campaigns flagged by rule-based checks (today vs. the 7-day baseline and vs. target CPL).
The "type" and "note" fields come from the rules and are facts; do not contradict them.

Write a concise Slack alert for the media buying team:
- Start with a one-line headline.
- For each campaign: what happened (use the numbers), the most likely cause, and a RECOMMENDATION
  for the media buyer to consider (e.g. rotate hooks, check landing page/tracking, a cautious +20% budget test).
- Be honest about uncertainty. Recommendations only, not commands. Plain text, no tables.

Flagged campaigns (JSON):
{data}
"""


def ask_llm(alerts):
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    prompt = PROMPT.format(data=json.dumps(alerts, indent=2))

    if provider == "openai" and os.getenv("OPENAI_API_KEY"):
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
            json={"model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"), "temperature": 0.3,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=60,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

    if provider == "gemini" and os.getenv("GEMINI_API_KEY"):
        model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]},
            json={"contents": [{"parts": [{"text": prompt}]}],
                  "generationConfig": {"temperature": 0.3, "maxOutputTokens": 4096}},
            timeout=60,
        )
        cand = r.json()["candidates"][0]
        text = "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []))
        if cand.get("finishReason") not in (None, "STOP"):
            text += f"\n\n[note: reply was cut off, finishReason={cand.get('finishReason')}]"
        return text


def plain_summary(alerts):
    """Fallback when there is no LLM key or the LLM call fails."""
    return "\n".join(f"- {a['campaign']} ({a['geo']}) [{a['type']}]: {a['note']} "
                     f"Spend ${a['spend_usd']}, CPL {a['cpl_usd']} vs target {a['target_cpl_usd']}."
                     for a in alerts)


def send_to_slack(text):
    url = os.getenv("SLACK_WEBHOOK_URL")
    if not url:
        print("\n[SLACK_WEBHOOK_URL not set - printing instead]\n")
        print(text)
        return
    r = requests.post(url, json={"text": text}, timeout=30)
    r.raise_for_status()
    print("Alert sent to Slack.")


def main():
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "campaigns.csv"
    alerts = find_alerts(pd.read_csv(csv_path))
    if not alerts:
        print("All campaigns within target KPIs. Nothing to send.")
        return
    print(f"Found {len(alerts)} flagged items.")
    try:
        summary = ask_llm(alerts) or plain_summary(alerts)
    except requests.RequestException as e:
        print(f"LLM request failed ({e}); using plain summary.")
        summary = plain_summary(alerts)
    send_to_slack(f":rotating_light: *Budget & Bid Guard - Daily Digest* ({len(alerts)} flagged)\n\n{summary}")


if __name__ == "__main__":
    main()
