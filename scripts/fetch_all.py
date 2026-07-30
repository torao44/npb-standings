"""
scripts/fetch_all.py

公式サイト（npb.jp 等）から自動で各種データを取得して data/ に JSON 保存する簡易スクリプト。
実際のサイト構造に合わせてセレクタを調整する必要があります。

使い方:
  python scripts/fetch_all.py --out-dir data

出力:
  data/standings.json
  data/schedule.json
  data/results.json
  data/rosters.json
  data/stats.json

注意:
- スクレイピングする際は対象サイトの利用規約に従ってください。
- 実運用では API があれば API を優先してください。
"""

from __future__ import annotations
import argparse
import json
import time
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import requests
from bs4 import BeautifulSoup

# 取得元のベース（必要に応じて変更）
BASE_URL = "https://npb.jp"
HEADERS = {
    "User-Agent": "npb-standings-bot/1.0 (+https://github.com/torao44/npb-standings)"
}


def safe_get(url: str, timeout: int = 15) -> str:
    print(f"Fetching: {url}")
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.text


def parse_standings(html: str) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    # TODO: 実際のセレクタに合わせて調整
    # 仮: テーブルを探してパースする
    table = soup.select_one("table")
    if not table:
        print("standings table not found; returning empty list", file=sys.stderr)
        return []

    rows = []
    for tr in table.select("tr")[1:]:
        cols = [td.get_text(strip=True) for td in tr.select("th,td")]
        if not cols:
            continue
        # 仮のカラム配置（要調整）
        item = {
            "team": cols[0] if len(cols) > 0 else "",
            "wins": cols[1] if len(cols) > 1 else "",
            "losses": cols[2] if len(cols) > 2 else "",
            "draws": cols[3] if len(cols) > 3 else "",
            "pct": cols[4] if len(cols) > 4 else "",
        }
        rows.append(item)
    return rows


def parse_schedule(html: str) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    # TODO: 実サイトのセレクタに合わせる
    events = []
    for li in soup.select(".schedule li"):
        text = li.get_text(" ", strip=True)
        events.append({"text": text})
    return events


def parse_results(html: str) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for row in soup.select(".results tr"):
        cols = [td.get_text(strip=True) for td in row.select("td")]
        if not cols:
            continue
        results.append({"cols": cols})
    return results


def parse_rosters(html: str) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    rosters = []
    for team in soup.select(".roster .team"):
        team_name = team.select_one(".team-name")
        players = [p.get_text(strip=True) for p in team.select(".player")]
        rosters.append({"team": team_name.get_text(strip=True) if team_name else "", "players": players})
    return rosters


def parse_stats(html: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    # 仮のパース
    leaders = []
    for row in soup.select(".leaders tr"):
        cols = [td.get_text(strip=True) for td in row.select("td")]
        if cols:
            leaders.append(cols)
    return {"leaders": leaders}


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Wrote: {path}")


def fetch_and_save(out_dir: Path) -> None:
    now = datetime.utcnow().isoformat() + "Z"

    # 1) Standings
    try:
        html = safe_get(f"{BASE_URL}/standings/")
        standings = parse_standings(html)
    except Exception as e:
        print(f"Failed to fetch standings: {e}", file=sys.stderr)
        standings = []
    write_json(out_dir / "standings.json", {"fetched_at": now, "source": f"{BASE_URL}/standings/", "standings": standings})
    time.sleep(1)

    # 2) Schedule
    try:
        html = safe_get(f"{BASE_URL}/games/")
        schedule = parse_schedule(html)
    except Exception as e:
        print(f"Failed to fetch schedule: {e}", file=sys.stderr)
        schedule = []
    write_json(out_dir / "schedule.json", {"fetched_at": now, "source": f"{BASE_URL}/games/", "schedule": schedule})
    time.sleep(1)

    # 3) Results
    try:
        html = safe_get(f"{BASE_URL}/results/")
        results = parse_results(html)
    except Exception as e:
        print(f"Failed to fetch results: {e}", file=sys.stderr)
        results = []
    write_json(out_dir / "results.json", {"fetched_at": now, "source": f"{BASE_URL}/results/", "results": results})
    time.sleep(1)

    # 4) Rosters
    try:
        html = safe_get(f"{BASE_URL}/teams/")
        rosters = parse_rosters(html)
    except Exception as e:
        print(f"Failed to fetch rosters: {e}", file=sys.stderr)
        rosters = []
    write_json(out_dir / "rosters.json", {"fetched_at": now, "source": f"{BASE_URL}/teams/", "rosters": rosters})
    time.sleep(1)

    # 5) Stats
    try:
        html = safe_get(f"{BASE_URL}/stats/")
        stats = parse_stats(html)
    except Exception as e:
        print(f"Failed to fetch stats: {e}", file=sys.stderr)
        stats = {}
    write_json(out_dir / "stats.json", {"fetched_at": now, "source": f"{BASE_URL}/stats/", "stats": stats})


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="data", help="Output directory for JSON files")
    args = parser.parse_args(argv)

    out_dir = Path(args.out_dir)
    try:
        fetch_and_save(out_dir)
    except Exception as e:
        print(f"Error during fetch_and_save: {e}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
