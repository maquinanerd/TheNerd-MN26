# TheNerd MN26

> Automated content pipeline for **The Nerd** — a WordPress-based news portal focused on tech, science, movies, and pop culture.

## Overview

TheNerd MN26 is a Python automation system that:

- Ingests articles from curated RSS & XML feeds
- Enriches content using the **Google Gemini AI** (rewriting, SEO optimization, categorization)
- Publishes polished posts directly to **WordPress via REST API**
- Tracks token/quota consumption per AI provider
- Generates an internal RSS feed and Google News-compatible sitemap

## Pipeline Summary

```
RSS/XML Feeds
     │
     ▼
Feed Ingestion (feeds.py)
     │
     ▼
AI Processing — Gemini (rewriter.py / ai_processor.py)
     │   ├── Title SEO optimization
     │   ├── Content rewriting
     │   ├── Categorization & tagging
     │   └── Internal linking
     ▼
WordPress Publisher (wordpress.py)
     │
     ▼
Sitemap & RSS Generation (rss_builder.py / synthetic_rss.py)
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys and WordPress credentials

# Run the pipeline
python main.py
```

## Project Structure

```
TheNerd-MN26/
├── app/              # Core application modules
│   ├── pipeline.py   # Main pipeline orchestration
│   ├── rewriter.py   # AI content processing
│   ├── wordpress.py  # WordPress REST API integration
│   ├── feeds.py      # RSS/XML feed ingestion
│   └── ...
├── docs/             # Full project documentation (see below)
├── templates/        # HTML/Gutenberg block templates
├── scripts/          # Utility & maintenance scripts
├── tests/            # Test suite
├── main.py           # Entrypoint
└── requirements.txt  # Python dependencies
```

## Documentation

| Category | Description | Path |
|---|---|---|
| Architecture | System design, component overview, data flow | [docs/architecture/](docs/architecture/) |
| Pipeline | Processing logic, changelogs, fixes | [docs/pipeline/](docs/pipeline/) |
| SEO Strategy | Google News SEO, editorial rules, image handling | [docs/seo/](docs/seo/) |
| RSS Sources | Feed configuration and sitemap specs | [docs/rss/](docs/rss/) |
| Deployment | Setup guides, checklists, quick references | [docs/deployment/](docs/deployment/) |
| Monetization | Token tracking, quota analysis, AI cost management | [docs/monetization/](docs/monetization/) |

## Key Technologies

- **Python 3.11+**
- **Google Gemini API** — content generation & rewriting
- **WordPress REST API** — headless publishing
- **TMDB API** — movie/series metadata enrichment
- **SQLite** — local article deduplication store
- **Makefile** — task automation

## Requirements

- Python 3.11+
- WordPress site with Application Password enabled
- Google AI Studio API key (Gemini)
- TMDB API key (optional, for movie content)

## Configuration

Copy `.env.example` to `.env` and fill in:

```dotenv
WP_URL=https://your-site.com
WP_USER=your_username
WP_APP_PASSWORD=your_app_password
GEMINI_API_KEY=your_gemini_key
TMDB_API_KEY=your_tmdb_key   # optional
```

---

*TheNerd MN26 — automated newsroom pipeline*
