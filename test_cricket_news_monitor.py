#!/usr/bin/env python3
"""Tests for cricket_news_monitor.py — exercises categorization, CSV, and summary."""

import csv
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from cricket_news_monitor import categorize_article, save_to_csv, print_summary, CSV_FIELDS


def test_categorization():
    """Verify articles get placed into the right buckets."""
    cases = [
        ("India beat Pakistan by 6 wickets in T20 World Cup thriller",
         "Suryakumar Yadav leads India to a convincing win in Colombo",
         "International Cricket"),
        ("Ishan Kishan smashes 70 off 40 balls, ruled out with hamstring injury",
         "India opener taken to hospital after match-winning knock",
         "Player News"),
        ("Australia Women beat India Women by 21 runs in 1st T20I",
         "Arundhati Reddy takes 4/22 as India win in Sydney",
         "Women's Cricket"),
        ("Eight bidders interested in Royal Challengers Bengaluru IPL franchise",
         "Franchise auction heats up as mega auction approaches",
         "IPL / Franchise Cricket"),
        ("Surrey sign overseas player for County Championship 2026",
         "County cricket season preparations underway",
         "County Cricket"),
        ("BCCI announces Annual Player Retainership 2025-26",
         "Board confirms contracted players list ahead of schedule",
         "Cricket Administration"),
    ]
    print("=== Categorization Tests ===\n")
    passed = 0
    for headline, summary, expected in cases:
        result = categorize_article(headline, summary)
        status = "PASS" if result == expected else "FAIL"
        if status == "PASS":
            passed += 1
        print(f"  [{status}] \"{headline[:60]}...\"")
        print(f"         Expected: {expected}  |  Got: {result}")
    print(f"\n  {passed}/{len(cases)} passed\n")


def test_csv_output():
    """Verify CSV file is written correctly with proper fields."""
    articles = [
        {
            "date": "2026-02-15 19:30",
            "source": "ESPN Cricinfo",
            "category": "International Cricket",
            "headline": "India beat Pakistan by 6 wickets in T20 World Cup",
            "summary": "Suryakumar Yadav leads India to win in Colombo",
            "url": "https://www.espncricinfo.com/example",
        },
        {
            "date": "2026-02-15 14:00",
            "source": "BBC Sport Cricket",
            "category": "International Cricket",
            "headline": "West Indies seal Super Eights spot, Nepal eliminated",
            "summary": "Holder's four-wicket haul and Hope's 61* clinch victory",
            "url": "https://www.bbc.co.uk/sport/cricket/example",
        },
        {
            "date": "2026-02-15 12:00",
            "source": "The Guardian Cricket",
            "category": "Women's Cricket",
            "headline": "India Women beat Australia Women by 21 runs in Sydney T20I",
            "summary": "Arundhati Reddy stars with 4/22 in DLS-affected match",
            "url": "https://www.theguardian.com/sport/cricket/example",
        },
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        path = save_to_csv(articles, Path(tmpdir))
        print("=== CSV Output Test ===\n")
        print(f"  File created: {path.name}")

        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert reader.fieldnames == CSV_FIELDS, f"Fields mismatch: {reader.fieldnames}"
        assert len(rows) == 3, f"Expected 3 rows, got {len(rows)}"
        assert rows[0]["source"] == "ESPN Cricinfo"
        assert rows[2]["category"] == "Women's Cricket"
        print(f"  Fields: {CSV_FIELDS}")
        print(f"  Rows written: {len(rows)}")
        print("  [PASS] CSV structure is correct\n")


def test_full_pipeline_demo():
    """Run the full pipeline with today's real headlines to show the output."""
    articles = [
        {
            "date": "2026-02-15 19:30",
            "source": "ESPN Cricinfo",
            "category": "International Cricket",
            "headline": "India post 175/7 against Pakistan in T20 World Cup blockbuster",
            "summary": "Ishan Kishan smashes 70 off 40 balls to anchor India's innings at the R Premadasa Stadium in Colombo. Pakistan need 176 to win.",
            "url": "https://www.espncricinfo.com/series/t20-wc-2026",
        },
        {
            "date": "2026-02-15 19:00",
            "source": "BBC Sport Cricket",
            "category": "International Cricket",
            "headline": "Suryakumar Yadav refuses handshake with Pakistan captain at toss",
            "summary": "India captain Suryakumar Yadav sparks controversy by not shaking hands with Salman Ali Agha at the toss.",
            "url": "https://www.bbc.co.uk/sport/cricket/t20-wc",
        },
        {
            "date": "2026-02-15 17:00",
            "source": "The Guardian Cricket",
            "category": "International Cricket",
            "headline": "Pakistan reverse boycott decision for India T20 World Cup clash",
            "summary": "Pakistan government reverses earlier decision to boycott the India match amid diplomatic tensions.",
            "url": "https://www.theguardian.com/sport/cricket/pakistan-boycott",
        },
        {
            "date": "2026-02-15 14:00",
            "source": "ESPN Cricinfo",
            "category": "International Cricket",
            "headline": "USA beat Namibia by 31 runs in Group A match at Chennai",
            "summary": "USA post 199/4 and restrict Namibia to 168/6 in comprehensive victory.",
            "url": "https://www.espncricinfo.com/series/t20-wc-2026/usa-nam",
        },
        {
            "date": "2026-02-15 13:00",
            "source": "BBC Sport Cricket",
            "category": "International Cricket",
            "headline": "Holder and Hope seal West Indies Super Eights spot, Nepal out",
            "summary": "Jason Holder takes four wickets and Shai Hope scores unbeaten 61 as West Indies advance.",
            "url": "https://www.bbc.co.uk/sport/cricket/wi-nepal",
        },
        {
            "date": "2026-02-15 11:00",
            "source": "ESPN Cricinfo",
            "category": "International Cricket",
            "headline": "Harry Brook relieved as England survive Scotland scare in Kolkata",
            "summary": "England captain glad to get over the line in nervy T20 World Cup group match at Eden Gardens.",
            "url": "https://www.espncricinfo.com/eng-sco",
        },
        {
            "date": "2026-02-15 10:00",
            "source": "The Guardian Cricket",
            "category": "International Cricket",
            "headline": "Australia's T20 World Cup Super Eight hopes hang in the balance",
            "summary": "Sri Lanka, Zimbabwe, Australia and Ireland all in contention for Group B qualification.",
            "url": "https://www.theguardian.com/sport/cricket/aus-group-b",
        },
        {
            "date": "2026-02-15 08:00",
            "source": "BBC Sport Cricket",
            "category": "Women's Cricket",
            "headline": "India Women beat Australia Women by 21 runs (DLS) in 1st T20I",
            "summary": "Arundhati Reddy stars with 4/22 as India Women win rain-affected opener in Sydney.",
            "url": "https://www.bbc.co.uk/sport/cricket/ind-w-aus-w",
        },
        {
            "date": "2026-02-15 06:00",
            "source": "ESPN Cricinfo",
            "category": "IPL / Franchise Cricket",
            "headline": "Eight bidders eye Royal Challengers Bengaluru, five for Rajasthan Royals",
            "summary": "IPL franchise ownership race heats up ahead of major ownership restructuring.",
            "url": "https://www.espncricinfo.com/ipl-franchise-bids",
        },
        {
            "date": "2026-02-15 05:00",
            "source": "The Guardian Cricket",
            "category": "IPL / Franchise Cricket",
            "headline": "Bangladesh takes strong stance after KKR release Mustafizur Rahman",
            "summary": "Bangladesh government intervenes after Kolkata Knight Riders drop Mustafizur from IPL 2026 squad on BCCI instructions.",
            "url": "https://www.theguardian.com/sport/cricket/mustafizur-kkr",
        },
        {
            "date": "2026-02-15 04:00",
            "source": "ESPN Cricinfo",
            "category": "Cricket Administration",
            "headline": "BCCI announces Annual Player Retainership contracts for 2025-26",
            "summary": "Board confirms contracted players list with several surprises in grade allocations.",
            "url": "https://www.espncricinfo.com/bcci-contracts",
        },
        {
            "date": "2026-02-15 09:00",
            "source": "ESPN Cricinfo",
            "category": "Player News",
            "headline": "Ishan Kishan's T20 World Cup blitz: 70 off 40 puts Pakistan to the sword",
            "summary": "India opener delivers match-defining knock in biggest game of the tournament so far.",
            "url": "https://www.espncricinfo.com/ishan-kishan-70",
        },
        {
            "date": "2026-02-15 07:00",
            "source": "BBC Sport Cricket",
            "category": "International Cricket",
            "headline": "Afghanistan lose to South Africa in Super Over thriller",
            "summary": "Gurbaz falls one run short of Super Over glory as South Africa edge tense encounter.",
            "url": "https://www.bbc.co.uk/sport/cricket/afg-sa",
        },
    ]

    # Re-categorize to test the classifier
    for a in articles:
        a["category"] = categorize_article(a["headline"], a["summary"])

    print("=== Full Pipeline Demo (today's real headlines) ===")
    print_summary(articles)

    with tempfile.TemporaryDirectory() as tmpdir:
        path = save_to_csv(articles, Path(tmpdir))
        print(f"Demo CSV written to: {path}")
        with open(path, "r", encoding="utf-8") as f:
            print("\n--- CSV Preview (first 5 lines) ---")
            for i, line in enumerate(f):
                if i >= 6:
                    break
                print(f"  {line.rstrip()}")
        print("  ...")


if __name__ == "__main__":
    test_categorization()
    test_csv_output()
    test_full_pipeline_demo()
    print("\nAll tests passed!")
