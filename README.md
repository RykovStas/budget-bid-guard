# Budget & Bid Guard

### AI-Assisted Paid Social Campaign Monitoring & Optimization

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Pandas](https://img.shields.io/badge/Data-Pandas-150458?logo=pandas)](https://pandas.pydata.org/)
[![AI](https://img.shields.io/badge/AI-Gemini%20%7C%20OpenAI-8E75B2)](https://ai.google.dev/)
[![Status](https://img.shields.io/badge/Status-Prototype-orange)]()

**Budget & Bid Guard** is a Python-based monitoring tool designed to help media buyers identify performance issues, detect creative fatigue, and spot potential scaling opportunities in paid social campaigns.

It combines deterministic performance rules with AI-generated explanations to turn raw campaign metrics into actionable daily insights.

Instead of manually reviewing every campaign, a media buyer can receive a concise report highlighting what needs attention.

---

## How It Works

The project follows a simple principle:

> **Rules decide. AI explains. Humans make the final decisions.**

The system uses Python to detect performance anomalies and optimization opportunities. An LLM (Google Gemini or OpenAI) then translates those findings into readable explanations and recommendations.

```text
Campaign Data (CSV)
        |
        v
Performance Analysis (Pandas)
        |
        v
Rule-Based Detection
        |
        v
AI Explanation (Gemini / OpenAI)
        |
        v
Daily Report (Slack / Terminal)
```

The AI does not independently analyze raw campaign data or make budget decisions. All alerts are triggered by deterministic, configurable rules. AI is used only to explain the detected findings.

## Key Features

- **Automated anomaly detection** — identifies unusual changes in campaign performance.
- **CPL monitoring** — detects when cost per lead exceeds campaign targets.
- **Creative fatigue detection** — identifies declining CTR combined with high frequency.
- **Scaling opportunity detection** — highlights campaigns with strong CPL performance and room for potential growth.
- **AI-powered explanations** — converts technical alerts into readable insights and recommendations.
- **Slack integration** — delivers daily reports through an incoming webhook.
- **Resilient fallback** — continues working if an AI provider is unavailable or Slack is not configured.
- **Configurable thresholds** — adjust monitoring rules without changing the source code.

---

## Detection Rules

| Rule | Detection Logic | What It Indicates |
|---|---|---|
| `SPEND_NO_LEADS` | Spend exceeds minimum threshold, but no leads are generated | Possible tracking, landing page or campaign issue |
| `CPL_SPIKE` | CPL exceeds target by at least 25% | Declining cost efficiency |
| `CREATIVE_FATIGUE` | CTR drops by at least 30% while frequency reaches 2.8+ | Possible audience or creative fatigue |
| `CTR_DROP` | CTR drops by at least 30%, but frequency remains below fatigue threshold | Performance decline requiring investigation |
| `SCALE_OPPORTUNITY` | CPL is at least 15% below target, baseline is within target, and frequency is below 2.0 | Potential opportunity for controlled scaling |

All thresholds can be adjusted through environment variables in `.env`.

The rules also include minimum spend, lead and impression requirements to reduce false positives caused by insufficient data.

---

## Demo: Example Analysis

The project includes a synthetic campaign dataset with deliberately injected performance scenarios.

Below is an example of an actual terminal report generated during a demo run.

**5 alerts detected across 4 campaigns.**

### Campaign Findings

| Campaign | Alert | Key Finding |
|---|---|---|
| DE_Lead_Static | Spend / No Leads | $82.63 spent, 0 leads |
| US_Fintech_Broad | CPL Spike | CPL $7.39 vs $5.89 target |
| UK_Loans_Video_A | CPL Spike | CPL $14.98 vs $6.19 target |
| UK_Loans_Video_A | Creative Fatigue | CTR down 47%, frequency 3.2 |
| FR_Lead_UGC | Scale Opportunity | CPL $4.18 vs $7.32 target |

### Example AI Recommendations

**1. Tracking or conversion issue — DE_Lead_Static**

- $82.63 spent with zero leads.
- Investigate conversion tracking, Pixel/CAPI events and landing page functionality.

**2. Cost efficiency decline — US_Fintech_Broad**

- CPL is approximately 25% above target.
- Monitor performance and investigate placements before making budget changes.

**3. Possible creative fatigue — UK_Loans_Video_A**

- CTR decreased by 47.4% compared with the 7-day baseline.
- Frequency reached 3.2.
- Consider testing fresh creatives.

**4. Potential scaling opportunity — FR_Lead_UGC**

- CPL is approximately 42.9% below target.
- 45 leads generated with frequency at 1.42.
- Consider a controlled budget increase and monitor performance.

*These recommendations are AI-generated examples based on synthetic campaign data. They are intended for human review, not automatic execution.*

---

## Tech Stack

| Technology | Purpose |
|---|---|
| Python | Core application logic |
| Pandas | Campaign data processing and analysis |
| NumPy | Synthetic data generation |
| Google Gemini API | AI-generated explanations |
| OpenAI API | Alternative LLM provider |
| Requests | API communication and Slack webhook integration |
| Pytest / unittest | Rule validation and testing |

---

## Project Structure

```text
budget-bid-guard/
│
├── guard.py             # Main monitoring and alerting logic
├── generate_data.py     # Synthetic campaign data generator
├── test_rules.py        # Automated tests for detection rules
│
├── requirements.txt     # Python dependencies
├── .env.example         # Environment configuration template
├── .gitignore           # Excluded files and secrets
└── README.md            # Project documentation
```

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/RykovStas/budget-bid-guard.git
cd budget-bid-guard
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and configure your preferred AI provider:

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_api_key
GEMINI_MODEL=your_supported_model
```

Alternatively, configure OpenAI.

Slack integration is optional. If no webhook is provided, the report is printed directly in the terminal.

The rule engine can also run without an AI API key, using plain-text alerts.

### 5. Generate demo data

```bash
python generate_data.py
```

This creates a synthetic `campaigns.csv` dataset containing sample campaigns and predefined performance scenarios.

### 6. Run the monitoring script

```bash
python guard.py
```

### 7. Run tests

```bash
python test_rules.py
```

---

## Design Decisions

**1. Deterministic logic over AI decision-making**

Performance alerts are generated by explicit Python rules. This makes the detection logic predictable, testable and easier to audit.

**2. Campaign-specific benchmarks**

Performance is evaluated against both the campaign's target CPL and its own recent 7-day baseline, rather than relying exclusively on generic benchmarks.

**3. Noise reduction**

Minimum sample-size requirements help prevent premature alerts when campaigns have insufficient spend, leads or impressions.

**4. Graceful degradation**

The monitoring process remains functional even when external services are unavailable:

- AI API unavailable → plain-text report.
- No Slack webhook → terminal output.
- No AI credentials → rule-based monitoring still works.

**5. Human-in-the-loop optimization**

The tool suggests areas for investigation and potential scaling. It never changes campaign budgets or launches ads automatically.

---

## Current Scope & Future Improvements

This is a working prototype built around synthetic campaign data.

The current version demonstrates the monitoring logic, alert generation, AI integration and reporting workflow. It does not yet connect to live advertising accounts.

Potential next steps:

- [ ] Meta Marketing API integration for live campaign data.
- [ ] Scheduled daily execution through cron or GitHub Actions.
- [ ] Historical performance storage and trend analysis.
- [ ] Additional anomaly detection rules.
- [ ] Campaign-level reporting dashboard.
- [ ] Automated alert prioritization.

---

## Author

**Stas Rykov**

Interested in performance marketing, data-driven optimization, Python automation and practical applications of AI in advertising workflows.

[GitHub Repository](https://github.com/RykovStas/budget-bid-guard)

---

*Disclaimer: This project is a portfolio prototype. All included campaign data is synthetic and does not represent actual advertising account performance.*