"""
scripts/fetch_all.py

NPB公式サイトから順位データを取得し、data/ に保存する。
主な目的:
  1. 最新順位 (standings.json)
  2. 日次順位履歴 (rank_history.json) の追記

使い方:
  python scripts/fetch_all.py --out-dir data
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup

YEAR = 2026
BASE = f"https://npb.jp/bis/{YEAR}/stats"
HEADERS = {
    "User-Agent": "npb-standings-bot/2.0 (+https://github.com/torao44/npb-standings)"
}

# 正式名マッピング
TEAM_ALIASES = {
    "阪神タイガース": "阪神タイガース",
    "阪神": "阪神タイガース",
    "読売ジャイアンツ": "読売ジャイアンツ",
    "巨人": "読売ジャイアンツ",
    "読売": "読売ジャイアンツ",
    "東京ヤクルトスワローズ": "東京ヤクルトスワローズ",
    "ヤクルト": "東京ヤクルトスワローズ",
    "横浜DeNAベイスターズ": "横浜DeNAベイスターズ",
    "DeNA": "横浜DeNAベイスターズ",
    "横浜DeNA": "横浜DeNAベイスターズ",
    "広島東洋カープ": "広島東洋カープ",
    "広島": "広島東洋カープ",
    "広島東洋": "広島東洋カープ",
    "中日ドラゴンズ": "中日ドラゴンズ",
    "中日": "中日ドラゴンズ",
    "福岡ソフトバンクホークス": "福岡ソフトバンクホークス",
    "ソフトバンク": "福岡ソフトバンクホークス",
    "福岡ソフトバンク": "福岡ソフトバンクホークス",
    "埼玉西武ライオンズ": "埼玉西武ライオンズ",
    "西武": "埼玉西武ライオンズ",
    "埼玉西武": "埼玉西武ライオンズ",
    "北海道日本ハムファイターズ": "北海道日本ハムファイターズ",
    "日本ハム": "北海道日本ハムファイターズ",
    "北海道日本ハム": "北海道日本ハムファイターズ",
    "オリックス・バファローズ": "オリックス・バファローズ",
    "オリックス": "オリックス・バファローズ",
    "千葉ロッテマリーンズ": "千葉ロッテマリーンズ",
    "ロッテ": "千葉ロッテマリーンズ",
    "千葉ロッテ": "千葉ロッテマリーンズ",
    "東北楽天ゴールデンイーグルス": "東北楽天ゴールデンイーグルス",
    "楽天": "東北楽天ゴールデンイーグルス",
    "東北楽天": "東北楽天ゴールデンイーグルス",
}


def normalize_team(name: str) -> str:
    name = name.strip()
    return TEAM_ALIASES.get(name, name)


def safe_get(url: str, timeout: int = 15) -> str:
    print(f"  GET {url}")
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text


def parse_standings_table(html: str) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html, "lxml")
    table = soup.select_one("div.stdtblmain table") or soup.find("table")
    if table is None:
        print("  [WARN] table not found", file=sys.stderr)
        return []

    rows: List[Dict[str, Any]] = []
    for tr in table.find_all("tr"):
        cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
        if len(cells) < 7:
            continue
        if cells[0] in ("チーム", "Team", "順位"):
            continue
        if not any(c.isdigit() for c in cells[1:4]):
            continue

        team = normalize_team(cells[0])
        try:
            item = {
                "rank": len(rows) + 1,
                "team": team,
                "games": int(cells[1]) if cells[1].isdigit() else 0,
                "wins": int(cells[2]) if cells[2].isdigit() else 0,
                "losses": int(cells[3]) if cells[3].isdigit() else 0,
                "draws": int(cells[4]) if cells[4].isdigit() else 0,
                "pct": cells[5],
                "gb": cells[6] if cells[6] not in ("", "--", "---") else "—",
            }
            rows.append(item)
        except (ValueError, IndexError):
            continue

    # 勝率で再ソート
    def pct_key(r):
        try:
            return float(r["pct"])
        except Exception:
            return 0.0

    rows.sort(key=lambda r: (-pct_key(r), -r["wins"]))
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return rows


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  Wrote {path}")


def update_rank_history(out_dir: Path, cl: List[Dict], pl: List[Dict]) -> None:
    hist_path = out_dir / "rank_history.json"
    if hist_path.exists():
        with hist_path.open(encoding="utf-8") as f:
            history = json.load(f)
    else:
        history = {"CL": {}, "PL": {}}

    today = datetime.now(timezone.utc).date().isoformat()

    for league, rows in (("CL", cl), ("PL", pl)):
        if not rows:
            continue
        if today not in history[league]:
            history[league][today] = {}
        for r in rows:
            history[league][today][r["team"]] = r["rank"]

    write_json(hist_path, history)


def fetch_and_save(out_dir: Path) -> None:
    now = datetime.now(timezone.utc).isoformat()
    print(f"[{now}] Fetching NPB standings...")

    # Central
    try:
        html = safe_get(f"{BASE}/std_c.html")
        cl = parse_standings_table(html)
        print(f"  CL teams: {len(cl)}")
    except Exception as e:
        print(f"  [ERROR] CL: {e}", file=sys.stderr)
        cl = []

    time.sleep(1.2)

    # Pacific
    try:
        html = safe_get(f"{BASE}/std_p.html")
        pl = parse_standings_table(html)
        print(f"  PL teams: {len(pl)}")
    except Exception as e:
        print(f"  [ERROR] PL: {e}", file=sys.stderr)
        pl = []

    # 保存
    payload = {
        "fetched_at": now,
        "year": YEAR,
        "central": cl,
        "pacific": pl,
    }
    write_json(out_dir / "standings.json", payload)

    # 履歴追記
    update_rank_history(out_dir, cl, pl)
    print("Done.")


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Fetch NPB standings")
    parser.add_argument("--out-dir", default="data", help="Output directory")
    args = parser.parse_args(argv)

    out_dir = Path(args.out_dir)
    try:
        fetch_and_save(out_dir)
    except Exception as e:
        print(f"Fatal: {e}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
