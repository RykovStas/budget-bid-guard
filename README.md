# Budget & Bid Guard

A lightweight AI-assisted performance monitoring tool for paid-social campaigns, that watches paid-social campaign stats, flags problems and scaling opportunities with
**deterministic rules**, lets an **LLM** explain them in plain language, and posts the result to **Slack**.

```
campaigns.csv  ->  rule checks (pandas)  ->  LLM summary (OpenAI / Gemini)  ->  Slack webhook
```

## Design decisions
- **Rules decide, the LLM explains.** Every flag and diagnosis comes from code, so it can be tested and audited.
  The LLM only turns flagged items into a readable alert, and its output is a recommendation for a human, never an action.
- **Noise protection.** Minimum spend, leads and impressions are required before a rule can fire,
  so a campaign with 2 leads does not trigger a "CPL spike".
- **Two reference points.** Today is compared to the campaign's target CPL and to its own 7-day baseline.
- **Graceful degradation.** No LLM key or an API error -> plain-text alert. No Slack webhook -> printed in the terminal.

## Rules
| Type | Fires when |
|---|---|
| `SPEND_NO_LEADS` | spend >= MIN_SPEND, zero leads today, baseline had leads |
| `CPL_SPIKE` | CPL >= target +25% and at least MIN_LEADS leads |
| `CREATIVE_FATIGUE` | CTR down >= 30% vs baseline and frequency >= 2.8 |
| `CTR_DROP` | same CTR drop, but frequency is low (not fatigue) |
| `SCALE_OPPORTUNITY` | spend >= $150, CPL >= 15% under target, baseline within target, frequency < 2.0 |

All thresholds are configurable in `.env`.

## Run it
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # add your keys (optional)
python generate_data.py       # creates fake campaigns.csv with injected anomalies
python guard.py               # analyse -> LLM -> Slack (or terminal preview)
python test_rules.py          # run the rule tests
```
To run daily, schedule `python guard.py` with cron or GitHub Actions. In production the CSV would be replaced by
a pull from the Meta Marketing API, and the same rules would apply unchanged.
