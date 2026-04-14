# Reportfy

> Python library and GitHub Action for automated GitHub project management reporting — with Monte Carlo forecasts, AI summaries (Mistral), and Discord notifications.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-0.1.0-orange.svg)](https://github.com/leds-conectafapes/reportfy/releases)

## Overview

Reportfy reads GitHub Issues from one or more repositories and generates a set of Markdown dashboards and PNG charts. It can optionally enrich every report with Mistral AI analysis and send summaries to Discord channels.

**What gets generated:**

- **Organization dashboard** — biweekly delivery tracking, burn-up chart, Monte Carlo completion forecast
- **Repository dashboards** — per-repo statistics, burn-up, velocity, Monte Carlo
- **Developer dashboards** — individual throughput, biweekly delivery, AI performance feedback and monthly competency evolution
- **Team dashboards** — team-level metrics, AI weekly summary and team maturity assessment
- **Collaboration network** — developer interaction graph, community detection, centrality metrics

---

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Output Structure](#output-structure)
- [GitHub Action](#github-action)
- [Python API](#python-api)
- [Feature Flags](#feature-flags)
- [AI Summaries (Mistral)](#ai-summaries-mistral)
- [Discord Notifications](#discord-notifications)
- [developers.json](#developersjson)
- [Three-Phase Pipeline](#three-phase-pipeline)
- [Publishing / Releases](#publishing--releases)

---

## Installation

### From PyPI

```bash
pip install reportfy
```

### From GitHub Packages

```bash
pip install reportfy \
  --index-url https://maven.pkg.github.com/leds-conectafapes/reportfy \
  --extra-index-url https://pypi.org/simple
```

### From Source

```bash
git clone https://github.com/leds-conectafapes/reportfy.git
cd reportfy
pip install -e .
```

**Requirements:** Python 3.10+

---

## Quick Start

### 1. Create a `.env` file

```dotenv
# Required
TOKEN=ghp_your_github_token
REPOSITORY=owner/repo          # single repo, or owner/* for all org repos

# Optional — AI
MISTRAL_API_KEY=your_mistral_key
ENABLE_AI_SUMMARIES=true

# Optional — Discord
DISCORD_BOT_TOKEN=your_bot_token
DISCORD_LEADERSHIP_CHANNEL=general
ENABLE_DISCORD_NOTIFICATIONS=false
```

### 2. Run

```bash
reportfy
```

Reports are saved to `./report/` by default.

---

## Configuration

All options can be set via environment variables (`.env` or shell) or CLI flags.

### Required

| Env Var | CLI Flag | Description |
|---------|----------|-------------|
| `TOKEN` | `--token` | GitHub Personal Access Token with `repo` and `read:org` scopes |
| `REPOSITORY` | `--repository` | Target as `owner/repo` or `owner/*` to include all org repositories |

### Report Generation

| Env Var | CLI Flag | Default | Description |
|---------|----------|---------|-------------|
| `REPORT_OUTPUT_DIR` | `--output-dir` | `./report` | Directory where files and charts are written |
| `MONTE_CARLO_SIMULATIONS` | `--simulations` | `1000` | Number of Monte Carlo iterations for delivery forecasting |
| `DEVELOPERS_CONFIG` | `--developers-config` | `./developers.json` | Path to GitHub → Discord ID mapping file (for DMs) |
| `COMMIT_REPORTS` | `--no-commit` (flag) | `true` | Auto-commit generated reports to git |

### Mistral AI (optional)

| Env Var | CLI Flag | Default | Description |
|---------|----------|---------|-------------|
| `MISTRAL_API_KEY` | `--mistral-key` | `""` | API key — leave empty to disable AI entirely |
| `MISTRAL_MODEL` | `--mistral-model` | `mistral-large-latest` | Model identifier (e.g. `mistral-small-latest`) |
| `ENABLE_AI_SUMMARIES` | `--ai-summaries` (flag) | `false` | Must be `true` together with a valid key to activate |

### Discord (optional)

| Env Var | CLI Flag | Default | Description |
|---------|----------|---------|-------------|
| `DISCORD_BOT_TOKEN` | `--discord-token` | `""` | Bot token — leave empty to disable Discord entirely |
| `DISCORD_LEADERSHIP_CHANNEL` | `--discord-channel` | `""` | Channel name for executive project notifications |
| `ENABLE_DISCORD_NOTIFICATIONS` | `--discord` (flag) | `false` | Must be `true` together with a valid token to activate |

### Feature Flags

| Env Var | CLI Flag | Default | Description |
|---------|----------|---------|-------------|
| `ENABLE_ORGANIZATION_REPORT` | `--no-organization` | `true` | Organization-level dashboard |
| `ENABLE_REPOSITORY_REPORT` | `--no-repository` | `true` | Per-repository dashboards |
| `ENABLE_DEVELOPER_REPORT` | `--no-developer` | `true` | Per-developer dashboards |
| `ENABLE_TEAM_REPORT` | `--no-team` | `true` | Per-team dashboards |
| `ENABLE_COLLABORATION_REPORT` | `--no-collaboration` | `true` | Collaboration network analysis |

---

## Output Structure

```
report/
├── organization_stats.md               # Org delivery, burn-up, Monte Carlo
├── repository_stats.md                 # All repos summary table
├── developer_stats.md                  # All developers summary table
├── teams.md                            # All teams summary index
├── collaboration_report.md             # Network analysis, communities, centrality
│
├── organization_charts/
│   ├── organization_biweekly.png       # Biweekly delivery (bar + line)
│   ├── organization_burnup.png         # Cumulative burn-up
│   ├── organization_monte_carlo.png    # Completion date distribution
│   └── organization_velocity_dist.png # Historical velocity histogram
│
├── charts_burnup/                      # Per-repo burn-up charts
├── charts_monte_carlo/                 # Per-repo Monte Carlo charts
├── charts_weekly/                      # Per-repo weekly velocity charts
│
├── developers/
│   ├── {login}.md                      # Stats: issues opened/closed, biweekly chart
│   └── {login}_feedback.md            # AI: performance + competency evolution (if AI enabled)
│
├── teams/
│   ├── {team}.md                       # Stats: team throughput, biweekly delivery
│   └── {team}_feedback.md             # AI: weekly summary + maturity assessment (if AI enabled)
│
├── collaboration/
│   └── {YYYY-MM}/
│       └── monthly.md                  # Monthly collaboration snapshot + AI analysis
│
└── collaboration_network.png           # Force-directed developer network graph
```

### Biweekly periods

All biweekly metrics always use fixed half-month windows:
- **1st – 15th** of each month
- **16th – last day** of each month

---

## GitHub Action

Reportfy ships as a Docker-based GitHub Action. The easiest way to use it is to add a workflow file to any repository — no Python setup required.

### Step 1 — Create a GitHub PAT

Go to **GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens** and create a token with:

- **Repository access:** All repositories (or select specific ones)
- **Permissions:**
  - `Issues` → Read-only
  - `Metadata` → Read-only
  - `Members` → Read-only (org level, required for team reports)

> Classic tokens: enable `repo` and `read:org` scopes.

### Step 2 — Add secrets to your repository

Go to **Settings → Secrets and variables → Actions → New repository secret** and add:

| Secret | When needed |
|--------|-------------|
| `TOKEN` | Always — GitHub PAT from Step 1 |
| `MISTRAL_API_KEY` | Only if using AI summaries |
| `DISCORD_BOT_TOKEN` | Only if using Discord notifications |

### Step 3 — Create the workflow file

Create `.github/workflows/reportfy.yml` in the repository where you want reports committed.

#### Minimal — generate and commit reports weekly

```yaml
# .github/workflows/reportfy.yml
name: Weekly Report

on:
  schedule:
    - cron: "0 8 * * 1"   # Every Monday at 08:00 UTC
  workflow_dispatch:       # Allow manual trigger from the Actions tab

jobs:
  report:
    runs-on: ubuntu-latest
    permissions:
      contents: write      # Required to commit reports back to the repo

    steps:
      - uses: actions/checkout@v4

      - uses: leds-conectafapes/reportfy@v0.1.0
        with:
          github_token: ${{ secrets.TOKEN }}
          repository: ${{ github.repository }}   # owner/repo of this repo
```

Reports are written to `./report/` and automatically committed with the message `chore(reports): auto-generate weekly reports [skip ci]`.

#### With AI summaries (Mistral)

```yaml
      - uses: leds-conectafapes/reportfy@v0.1.0
        with:
          github_token: ${{ secrets.TOKEN }}
          repository: ${{ github.repository }}
          mistral_api_key: ${{ secrets.MISTRAL_API_KEY }}
          mistral_model: "mistral-large-latest"   # or mistral-small-latest
          enable_ai_summaries: "true"
```

This generates separate `{login}_feedback.md` and `{team}_feedback.md` files with AI-written performance analysis, monthly competency evolution, and team maturity assessments.

#### Scanning an entire organization

Use `owner/*` as the repository to include all repositories in the organization:

```yaml
      - uses: leds-conectafapes/reportfy@v0.1.0
        with:
          github_token: ${{ secrets.TOKEN }}
          repository: "leds-conectafapes/*"
```

#### With Discord notifications

First, create a `developers.json` file at the root of the repository (see [developers.json](#developersjson)), then:

```yaml
      - uses: leds-conectafapes/reportfy@v0.1.0
        with:
          github_token: ${{ secrets.TOKEN }}
          repository: ${{ github.repository }}
          discord_bot_token: ${{ secrets.DISCORD_BOT_TOKEN }}
          discord_leadership_channel: "leadership"
          developers_config: "./developers.json"
          enable_discord_notifications: "true"
```

#### Complete example — all features enabled

```yaml
# .github/workflows/reportfy.yml
name: Weekly Report

on:
  schedule:
    - cron: "0 8 * * 1"
  workflow_dispatch:

jobs:
  report:
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - uses: actions/checkout@v4

      - uses: leds-conectafapes/reportfy@v0.1.0
        with:
          github_token: ${{ secrets.TOKEN }}
          repository: "leds-conectafapes/*"
          report_output_dir: "./report"
          monte_carlo_simulations: "1000"
          mistral_api_key: ${{ secrets.MISTRAL_API_KEY }}
          mistral_model: "mistral-large-latest"
          discord_bot_token: ${{ secrets.DISCORD_BOT_TOKEN }}
          discord_leadership_channel: "leadership"
          developers_config: "./developers.json"
          enable_organization_report: "true"
          enable_repository_report: "true"
          enable_developer_report: "true"
          enable_team_report: "true"
          enable_collaboration_report: "true"
          enable_ai_summaries: "true"
          enable_discord_notifications: "true"
          commit_reports: "true"
```

#### Disabling specific reports

Use the `enable_*` flags to skip reports you don't need:

```yaml
      - uses: leds-conectafapes/reportfy@v0.1.0
        with:
          github_token: ${{ secrets.TOKEN }}
          repository: ${{ github.repository }}
          enable_repository_report: "false"    # skip per-repo dashboards
          enable_collaboration_report: "false" # skip network analysis
```

### Action Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `github_token` | Yes | — | GitHub PAT with `repo` + `read:org` scopes |
| `repository` | Yes | — | `owner/repo` or `owner/*` for all org repos |
| `report_output_dir` | No | `./report` | Directory where reports are written |
| `monte_carlo_simulations` | No | `1000` | Simulation iterations for delivery forecasting |
| `mistral_api_key` | No | `""` | Mistral API key — leave empty to disable AI |
| `mistral_model` | No | `mistral-large-latest` | Mistral model identifier |
| `discord_bot_token` | No | `""` | Discord bot token — leave empty to disable notifications |
| `discord_leadership_channel` | No | `""` | Channel name for executive project summary |
| `developers_config` | No | `./developers.json` | Path to GitHub→Discord ID mapping file |
| `enable_organization_report` | No | `true` | Organization-level dashboard |
| `enable_repository_report` | No | `true` | Per-repository dashboards |
| `enable_developer_report` | No | `true` | Per-developer dashboards |
| `enable_team_report` | No | `true` | Per-team dashboards |
| `enable_collaboration_report` | No | `true` | Collaboration network analysis |
| `enable_ai_summaries` | No | `false` | AI analysis via Mistral (requires `mistral_api_key`) |
| `enable_discord_notifications` | No | `false` | Discord notifications (requires `discord_bot_token`) |
| `commit_reports` | No | `true` | Auto-commit generated reports to git |

### Action Outputs

Use outputs to reference generated files in subsequent steps:

```yaml
    steps:
      - uses: actions/checkout@v4

      - id: reportfy
        uses: leds-conectafapes/reportfy@v0.1.0
        with:
          github_token: ${{ secrets.TOKEN }}
          repository: ${{ github.repository }}

      - name: Upload reports as artifact
        uses: actions/upload-artifact@v4
        with:
          name: reports
          path: ${{ steps.reportfy.outputs.organization_report }}
```

| Output | Description |
|--------|-------------|
| `organization_report` | Path to `organization_stats.md` |
| `repository_report` | Path to `repository_stats.md` |
| `developer_report` | Path to `developer_stats.md` |
| `team_report` | Path to `teams.md` |
| `collaboration_report` | Path to `collaboration_report.md` |

---

## Python API

Use Reportfy as a library in your own scripts:

```python
from reportfy.core.config import ReportConfig
from reportfy.controllers.report_controller import ReportController

config = ReportConfig(
    github_token="ghp_...",
    repository="owner/repo",            # or "owner/*"
    output_dir="./report",
    monte_carlo_simulations=1000,
    # AI (optional)
    mistral_api_key="...",
    mistral_model="mistral-large-latest",
    enable_ai_summaries=True,
    # Discord (optional)
    discord_bot_token="...",
    discord_leadership_channel="general",
    enable_discord_notifications=False,
    # Feature flags
    enable_organization_report=True,
    enable_repository_report=True,
    enable_developer_report=True,
    enable_team_report=True,
    enable_collaboration_report=True,
    commit_reports=False,
)

ReportController(config).run()
```

### Running individual controllers

```python
from reportfy.core.config import ReportConfig
from reportfy.core.fetcher import GitHubFetcher
from reportfy.controllers.developer_controller import DeveloperController
from reportfy.controllers.team_controller import TeamController

config = ReportConfig(github_token="ghp_...", repository="owner/repo")
fetcher = GitHubFetcher(config)
data = fetcher.fetch_all()

# Phase 1 — generate stats files
dev = DeveloperController(config, data["issues"])
dev.run()

# Phase 2 — generate AI feedback files (requires AI config)
dev.run_ai()

# Same for teams
team = TeamController(config, data["issues"], data["team_members"])
team.run()
team.run_ai()
```

---

## Feature Flags

Feature flags control which report types are generated. Disabling a flag skips both its file generation and AI analysis.

| Flag | What it generates |
|------|-------------------|
| `ENABLE_ORGANIZATION_REPORT` | `organization_stats.md` + 4 charts + AI strategic analysis |
| `ENABLE_REPOSITORY_REPORT` | `repository_stats.md` + per-repo burn-up, Monte Carlo, weekly charts |
| `ENABLE_DEVELOPER_REPORT` | `developer_stats.md` + `developers/{login}.md` + `{login}_feedback.md` |
| `ENABLE_TEAM_REPORT` | `teams.md` + `teams/{team}.md` + `{team}_feedback.md` |
| `ENABLE_COLLABORATION_REPORT` | `collaboration_report.md` + `collaboration_network.png` + monthly snapshots |

---

## AI Summaries (Mistral)

When `ENABLE_AI_SUMMARIES=true` and `MISTRAL_API_KEY` is set, Reportfy runs a second pass over the generated files and produces AI-enriched content:

| Report | AI Output | File |
|--------|-----------|------|
| Organization | Strategic project analysis | appended to `organization_stats.md` |
| Developer | Performance feedback + monthly competency evolution | `developers/{login}_feedback.md` |
| Team | Weekly summary + team maturity assessment | `teams/{team}_feedback.md` |
| Teams index | Executive summary across all teams | appended to `teams.md` |
| Collaboration | Network interpretation and recommendations | appended to `collaboration_report.md` + monthly files |

AI feedback files are **separate** from stats files so you can commit/share them independently.

The AI phase runs **after** all files are generated (Phase 2) and **before** Discord notifications (Phase 3), ensuring Discord always sends the fully enriched content.

---

## Discord Notifications

When `ENABLE_DISCORD_NOTIFICATIONS=true` and `DISCORD_BOT_TOKEN` is set, Reportfy sends:

| Sender | Target | Content |
|--------|--------|---------|
| `DeveloperMessageSender` | Developer DMs | Individual performance summary |
| `CompetenceMessageSender` | Developer DMs | Competency profile |
| `TeamWeeklySender` | Team channels | Weekly team highlights |
| `TeamsGeneralSender` | Leadership channel | Cross-team executive summary |
| `ProjectMessageSender` | Leadership channel | Project status and Monte Carlo forecast |

Developer DMs require a [`developers.json`](#developersjson) file mapping GitHub logins to Discord user IDs.

---

## developers.json

To receive Discord DMs, create a `developers.json` file mapping GitHub logins to Discord user IDs:

```json
[
  {
    "github_id": "octocat",
    "discord_id": 123456789012345678
  },
  {
    "github_id": "torvalds",
    "discord_id": 987654321098765432
  }
]
```

The file path defaults to `./developers.json` and can be overridden with `DEVELOPERS_CONFIG` or `--developers-config`.

---

## Three-Phase Pipeline

Reportfy separates execution into three independent phases so each can succeed or fail without affecting the others:

```
Phase 1 — Generate
  OrganizationController.run()
  RepositoryController.run()
  DeveloperController.run()      → developers/{login}.md
  TeamController.run()           → teams/{team}.md
  CollaborationController.run()  → collaboration_report.md

Phase 2 — AI Analysis  (skipped if ENABLE_AI_SUMMARIES=false)
  OrganizationController.run_ai()
  DeveloperController.run_ai()   → developers/{login}_feedback.md
  TeamController.run_ai()        → teams/{team}_feedback.md
  CollaborationController.run_ai()

Phase 3 — Notifications  (skipped if ENABLE_DISCORD_NOTIFICATIONS=false)
  DeveloperMessageSender.send()
  CompetenceMessageSender.send()
  TeamWeeklySender.send()
  TeamsGeneralSender.send()
  ProjectMessageSender.send()
```

This means you can run Phase 1 on every push, enable Phase 2 only on weekly schedules, and toggle Phase 3 without changing report generation.

---

## Publishing / Releases

Push a version tag to trigger the publish workflow:

```bash
git tag v0.1.0
git push origin v0.1.0
```

The [publish workflow](.github/workflows/publish.yml) will:

1. Build the `sdist` and `wheel` with `python -m build`
2. Publish to **GitHub Packages** (always)
3. Publish to **PyPI** (if `PYPI_API_TOKEN` secret is set)
4. Create a **GitHub Release** with the built artifacts

---

## License

MIT — see [LICENSE](LICENSE) for details.
