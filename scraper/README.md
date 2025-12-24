# 🕉️ Ashtadhyayi.com Book Scraper

Sanskrit grammar books from [ashtadhyayi.com](https://ashtadhyayi.com) → Well-formatted Markdown

## 📚 Available Books

| Book | Entries | Time |
|------|---------|------|
| `shivasutra` | 14 | ~30 sec |
| `sutraani` | 3981 | ~2 hrs |
| `dhatu` | ~2000 | ~1 hr |
| `pratyahara` | 44 | ~1 min |
| `ganapatha` | ~450 | ~15 min |

## 🚀 Quick Start

### Local Run
```bash
# Install dependencies
pip install selenium beautifulsoup4

# Scrape shivasutra (fastest)
python scraper/ashtadhyayi_scraper.py --book shivasutra

# Test sutraani with limit
python scraper/ashtadhyayi_scraper.py --book sutraani --limit 20

# Full sutraani (takes ~2 hours)
python scraper/ashtadhyayi_scraper.py --book sutraani
```

### GitHub Actions (Recommended for large books)

1. Go to **Actions** tab in your repo
2. Click **"Scrape Ashtadhyayi Books"** workflow
3. Click **"Run workflow"**
4. Select book and optional limit  
5. Click green **"Run workflow"** button
6. Download artifacts when complete

## 📁 Output Structure

```
books/
├── shivasutra/
│   ├── README.md
│   └── entry_01.md ... entry_14.md
└── sutraani/
    ├── README.md
    └── adhyaya_1/
        └── pada_1/
            └── sutra_001.md
```

## ⚙️ CLI Options

```bash
python scraper/ashtadhyayi_scraper.py --help

Options:
  --book, -b      Book name (required)
  --output, -o    Output directory (default: ./books)
  --limit, -l     Max entries to scrape
  --delay, -d     Delay between requests (default: 1.5s)
  --no-headless   Show browser window
  --quiet, -q     Suppress progress messages
```
