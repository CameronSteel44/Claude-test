#!/usr/bin/env python3
"""
Cricket News Monitor
====================
Fetches cricket news from major sources (ESPN Cricinfo, BBC Sport Cricket,
The Guardian Cricket) via RSS feeds and web scraping, categorizes articles,
and saves a daily summary to CSV.

Usage:
    python3 cricket_news_monitor.py              # Fetch today's news
    python3 cricket_news_monitor.py --days 3     # Fetch last 3 days of news
    python3 cricket_news_monitor.py --output DIR  # Custom output directory
"""

import argparse
import csv
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Source configuration — RSS feeds + HTML fallback URLs
# ---------------------------------------------------------------------------

SOURCES = {
    "ESPN Cricinfo": {
        "rss_url": "https://www.espncricinfo.com/rss/content/story/feeds/0.xml",
        "fallback_url": "https://www.espncricinfo.com/cricket-news",
    },
    "BBC Sport Cricket": {
        "rss_url": "https://feeds.bbci.co.uk/sport/cricket/rss.xml",
        "fallback_url": "https://www.bbc.co.uk/sport/cricket",
    },
    "The Guardian Cricket": {
        "rss_url": "https://www.theguardian.com/sport/cricket/rss",
        "fallback_url": "https://www.theguardian.com/sport/cricket",
    },
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}

# ---------------------------------------------------------------------------
# Category classification
# ---------------------------------------------------------------------------

CATEGORY_PATTERNS = {
    "International Cricket": [
        r"\b(test match|odi|t20i|world cup|icc|international|tour|series)\b",
        r"\b(ashes|india|australia|england|pakistan|south africa|new zealand)\b",
        r"\b(west indies|sri lanka|bangladesh|afghanistan|zimbabwe|ireland)\b",
        r"\b(champions trophy|wtc|world test championship)\b",
    ],
    "County Cricket": [
        r"\b(county|championship|vitality blast|hundred|t20 blast)\b",
        r"\b(somerset|surrey|essex|yorkshire|lancashire|kent|sussex)\b",
        r"\b(middlesex|nottinghamshire|warwickshire|hampshire|durham)\b",
        r"\b(gloucestershire|leicestershire|worcestershire|derbyshire)\b",
    ],
    "IPL / Franchise Cricket": [
        r"\b(ipl|indian premier league|big bash|bbl|psl|cpl|sa20|lpl)\b",
        r"\b(mumbai indians|chennai super kings|royal challengers)\b",
        r"\b(sunrisers|rajasthan royals|delhi capitals|punjab kings)\b",
        r"\b(franchise|auction|mega auction|retention)\b",
    ],
    "Player News": [
        r"\b(retire|retirement|injury|injured|comeback|contract|transfer)\b",
        r"\b(milestone|century|hat-trick|record|debut|dropped|selected)\b",
        r"\b(fitness|surgery|rehab|ruled out|doubtful|replacement)\b",
    ],
    "Women's Cricket": [
        r"\b(women'?s?|wpl|wbbl|wodi|wt20i)\b",
        r"\b(women'?s? ashes|women'?s? world cup|women'?s? ipl)\b",
    ],
    "Cricket Administration": [
        r"\b(bcci|ecb|cricket australia|pcb|nzc|board|governance)\b",
        r"\b(schedule|fixture|regulation|rule change|corruption|ban)\b",
        r"\b(broadcast|tv rights|revenue|sponsor)\b",
    ],
}


def categorize_article(headline, summary):
    """Classify an article into a cricket topic category."""
    text = f"{headline} {summary}".lower()

    # Women's Cricket is checked first — "Australia Women" should not
    # be classified as International just because "Australia" matches.
    for pat in CATEGORY_PATTERNS["Women's Cricket"]:
        if re.search(pat, text, re.IGNORECASE):
            return "Women's Cricket"

    scores = {}
    for category, patterns in CATEGORY_PATTERNS.items():
        if category == "Women's Cricket":
            continue
        score = sum(1 for p in patterns if re.search(p, text, re.IGNORECASE))
        if score > 0:
            scores[category] = score
    if scores:
        return max(scores, key=scores.get)
    return "General Cricket"


# ---------------------------------------------------------------------------
# RSS date parsing
# ---------------------------------------------------------------------------

def parse_rss_date(date_str):
    """Parse various RSS date formats into a timezone-aware datetime."""
    if not date_str:
        return None
    # Try RFC 2822 (standard RSS)
    try:
        return parsedate_to_datetime(date_str)
    except Exception:
        pass
    # Try ISO 8601 variants
    for fmt in [
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
    ]:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


def _get_text(element, tag, namespaces):
    """Get text of a child element, trying plain and namespaced lookups."""
    child = element.find(tag)
    if child is not None and child.text:
        return child.text.strip()
    for uri in namespaces.values():
        child = element.find(f"{{{uri}}}{tag}")
        if child is not None and child.text:
            return child.text.strip()
    return None


# ---------------------------------------------------------------------------
# RSS fetching
# ---------------------------------------------------------------------------

def fetch_rss_articles(source_name, config, cutoff):
    """Fetch and parse articles from an RSS feed, fall back to HTML scrape."""
    rss_url = config["rss_url"]
    print(f"  Fetching RSS: {rss_url}")

    try:
        resp = requests.get(rss_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  [WARN] RSS failed for {source_name}: {e}")
        return fetch_fallback_articles(source_name, config)

    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError as e:
        print(f"  [WARN] RSS parse error for {source_name}: {e}")
        return fetch_fallback_articles(source_name, config)

    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "dc": "http://purl.org/dc/elements/1.1/",
        "media": "http://search.yahoo.com/mrss/",
    }

    items = root.findall(".//item")
    if not items:
        items = root.findall(".//{http://www.w3.org/2005/Atom}entry")

    articles = []
    for item in items:
        title = _get_text(item, "title", ns)
        if not title:
            continue

        description = _get_text(item, "description", ns)
        if not description:
            description = _get_text(item, "summary", ns)

        # Strip HTML tags from description
        if description:
            description = BeautifulSoup(description, "lxml").get_text(" ", strip=True)
            if len(description) > 300:
                description = description[:297] + "..."

        link = _get_text(item, "link", ns)
        if not link:
            link_el = item.find("{http://www.w3.org/2005/Atom}link")
            if link_el is not None:
                link = link_el.get("href", "")

        pub_str = (_get_text(item, "pubDate", ns)
                   or _get_text(item, "updated", ns)
                   or _get_text(item, "date", ns))
        pub_date = parse_rss_date(pub_str)

        if pub_date and pub_date < cutoff:
            continue

        articles.append({
            "date": pub_date.strftime("%Y-%m-%d %H:%M") if pub_date else "Unknown",
            "source": source_name,
            "category": categorize_article(title, description or ""),
            "headline": title.strip(),
            "summary": (description or "No summary available.").strip(),
            "url": (link or "").strip(),
        })

    return articles


# ---------------------------------------------------------------------------
# Fallback: HTML scraping
# ---------------------------------------------------------------------------

def fetch_fallback_articles(source_name, config):
    """Scrape the website directly when RSS is unavailable."""
    url = config["fallback_url"]
    print(f"  Falling back to HTML scrape: {url}")

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  [ERROR] Scrape failed for {source_name}: {e}")
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if "espncricinfo" in url:
        return _scrape_generic(soup, source_name, today,
                               "a[href*='/story/'], a[href*='/cricket-news/']",
                               "https://www.espncricinfo.com")
    elif "bbc" in url:
        return _scrape_generic(soup, source_name, today,
                               "a[href*='/sport/cricket/']",
                               "https://www.bbc.co.uk")
    elif "guardian" in url:
        return _scrape_generic(soup, source_name, today,
                               "a[data-link-name='article'], a[href*='/sport/cricket/']",
                               "https://www.theguardian.com")
    return []


def _scrape_generic(soup, source_name, today, selector, base_url):
    """Generic headline scraper for any source."""
    articles = []
    seen = set()

    for tag in soup.select(selector):
        title = tag.get_text(strip=True)
        if not title or len(title) < 15 or title.lower() in seen:
            continue
        seen.add(title.lower())

        href = tag.get("href", "")
        if href and not href.startswith("http"):
            href = f"{base_url}{href}"

        articles.append({
            "date": today,
            "source": source_name,
            "category": categorize_article(title, ""),
            "headline": title,
            "summary": f"Headline scraped from {source_name} (visit URL for full article).",
            "url": href,
        })
        if len(articles) >= 20:
            break

    return articles


# ---------------------------------------------------------------------------
# CSV output
# ---------------------------------------------------------------------------

CSV_FIELDS = ["date", "source", "category", "headline", "summary", "url"]


def save_to_csv(articles, output_dir):
    """Write articles to a date-stamped CSV file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    today_str = datetime.now().strftime("%Y-%m-%d")
    filepath = output_dir / f"cricket_news_{today_str}.csv"

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(articles)

    return filepath


# ---------------------------------------------------------------------------
# Pretty-print summary
# ---------------------------------------------------------------------------

def print_summary(articles):
    """Print a human-readable summary grouped by category."""
    if not articles:
        print("\nNo cricket news articles found for the specified period.")
        return

    print(f"\n{'=' * 70}")
    print(f"  CRICKET NEWS DAILY SUMMARY")
    print(f"  {datetime.now().strftime('%A, %B %d, %Y')}")
    print(f"{'=' * 70}")
    print(f"  Total articles: {len(articles)}")

    source_counts = {}
    for a in articles:
        source_counts[a["source"]] = source_counts.get(a["source"], 0) + 1
    for src, count in sorted(source_counts.items()):
        print(f"    {src}: {count}")

    by_category = {}
    for a in articles:
        by_category.setdefault(a["category"], []).append(a)

    for category in sorted(by_category):
        cat_articles = by_category[category]
        print(f"\n  [{category}] ({len(cat_articles)} articles)")
        print(f"  {'-' * 50}")
        for a in cat_articles:
            print(f"  * {a['headline']}")
            print(f"    Source: {a['source']}  |  Date: {a['date']}")
            if a["summary"] and "No summary" not in a["summary"] and "scraped" not in a["summary"].lower():
                line = a["summary"][:120]
                if len(a["summary"]) > 120:
                    line += "..."
                print(f"    {line}")
            print()

    print(f"{'=' * 70}\n")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Cricket News Monitor - fetch and summarize cricket news"
    )
    parser.add_argument(
        "--days", type=int, default=1,
        help="Number of days to look back (default: 1)",
    )
    parser.add_argument(
        "--output", type=str, default="output",
        help="Output directory for CSV files (default: ./output)",
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Suppress the printed summary (only write CSV)",
    )
    args = parser.parse_args()

    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
    output_dir = Path(args.output)

    print("Cricket News Monitor")
    print(f"Looking for articles from the past {args.days} day(s)...")
    print(f"Cutoff: {cutoff.strftime('%Y-%m-%d %H:%M UTC')}\n")

    all_articles = []
    for source_name, config in SOURCES.items():
        print(f"[{source_name}]")
        articles = fetch_rss_articles(source_name, config, cutoff)
        print(f"  Found {len(articles)} article(s)\n")
        all_articles.extend(articles)

    # Deduplicate by headline
    seen = set()
    unique = []
    for a in all_articles:
        key = a["headline"].lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(a)

    # Sort by date descending
    unique.sort(key=lambda x: (x["date"], x["source"]), reverse=True)

    csv_path = save_to_csv(unique, output_dir)
    print(f"Saved {len(unique)} articles to: {csv_path}")

    if not args.quiet:
        print_summary(unique)

    return 0


if __name__ == "__main__":
    sys.exit(main())
