"""
NPB 順位表 & 順位推移アプリ
- NPB公式サイトから最新順位を取得
- 日次スナップショットから順位推移を描画
"""

import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import plotly.graph_objects as go
import json
import datetime
from pathlib import Path
from typing import Optional

# ------------------------------------------------------------
# 設定
# ------------------------------------------------------------
st.set_page_config(
    page_title="NPB順位表 2026",
    page_icon="⚾",
    layout="wide",
    initial_sidebar_state="collapsed",
)

YEAR = 2026
DATA_DIR = Path(__file__).parent / "data"
HISTORY_FILE = DATA_DIR / "rank_history.json"

# チーム正式名 → 略称・色
TEAM_META = {
    # セ・リーグ
    "阪神タイガース": {"short": "阪神", "color": "#FFD700", "league": "CL"},
    "読売ジャイアンツ": {"short": "巨人", "color": "#FF6600", "league": "CL"},
    "東京ヤクルトスワローズ": {"short": "ヤクルト", "color": "#0068B7", "league": "CL"},
    "横浜DeNAベイスターズ": {"short": "DeNA", "color": "#0067C0", "league": "CL"},
    "広島東洋カープ": {"short": "広島", "color": "#E50012", "league": "CL"},
    "中日ドラゴンズ": {"short": "中日", "color": "#0D2E8C", "league": "CL"},
    # パ・リーグ
    "福岡ソフトバンクホークス": {"short": "ソフトバンク", "color": "#F7A900", "league": "PL"},
    "埼玉西武ライオンズ": {"short": "西武", "color": "#0067C5", "league": "PL"},
    "北海道日本ハムファイターズ": {"short": "日本ハム", "color": "#1E90FF", "league": "PL"},
    "オリックス・バファローズ": {"short": "オリックス", "color": "#1A1A1A", "league": "PL"},
    "千葉ロッテマリーンズ": {"short": "ロッテ", "color": "#000000", "league": "PL"},
    "東北楽天ゴールデンイーグルス": {"short": "楽天", "color": "#8B0000", "league": "PL"},
}

# 略称から正式名への逆引き（一部別名対応）
SHORT_TO_FULL = {v["short"]: k for k, v in TEAM_META.items()}
SHORT_TO_FULL.update({
    "阪神": "阪神タイガース",
    "巨人": "読売ジャイアンツ",
    "ヤクルト": "東京ヤクルトスワローズ",
    "DeNA": "横浜DeNAベイスターズ",
    "広島": "広島東洋カープ",
    "中日": "中日ドラゴンズ",
    "ソフトバンク": "福岡ソフトバンクホークス",
    "西武": "埼玉西武ライオンズ",
    "日本ハム": "北海道日本ハムファイターズ",
    "オリックス": "オリックス・バファローズ",
    "ロッテ": "千葉ロッテマリーンズ",
    "楽天": "東北楽天ゴールデンイーグルス",
    "読売": "読売ジャイアンツ",
    "横浜DeNA": "横浜DeNAベイスターズ",
    "広島東洋": "広島東洋カープ",
    "福岡ソフトバンク": "福岡ソフトバンクホークス",
    "埼玉西武": "埼玉西武ライオンズ",
    "北海道日本ハム": "北海道日本ハムファイターズ",
    "千葉ロッテ": "千葉ロッテマリーンズ",
    "東北楽天": "東北楽天ゴールデンイーグルス",
})


# ------------------------------------------------------------
# ユーティリティ
# ------------------------------------------------------------
def short_name(full: str) -> str:
    return TEAM_META.get(full, {}).get("short", full)


def team_color(full: str) -> str:
    return TEAM_META.get(full, {}).get("color", "#888888")


# ------------------------------------------------------------
# スクレイピング
# ------------------------------------------------------------
@st.cache_data(ttl=1800, show_spinner="順位表を取得中...")
def fetch_standings(league: str) -> Optional[pd.DataFrame]:
    """
    league: 'c' (Central) or 'p' (Pacific)
    """
    url = f"https://npb.jp/bis/{YEAR}/stats/std_{league}.html"
    try:
        r = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; npb-standings/2.0)"},
            timeout=15,
        )
        r.raise_for_status()
        r.encoding = r.apparent_encoding or "utf-8"
    except Exception as e:
        st.warning(f"取得失敗 ({league}): {e}")
        return None

    soup = BeautifulSoup(r.text, "lxml")

    # メインテーブルを探す（.stdtblmain が存在する場合を優先）
    table = soup.select_one("div.stdtblmain table") or soup.find("table")
    if table is None:
        return None

    rows = []
    for tr in table.find_all("tr"):
        cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
        if len(cells) < 7:
            continue
        # ヘッダー行をスキップ
        if cells[0] in ("チーム", "Team", "順位"):
            continue
        # 数字を含む行だけ採用
        if not any(c.isdigit() for c in cells[1:4]):
            continue

        team_raw = cells[0]
        # 略称が混ざっている場合の正規化
        team = SHORT_TO_FULL.get(team_raw, team_raw)
        if team not in TEAM_META:
            # 部分一致で救済
            for full in TEAM_META:
                if team_raw in full or full in team_raw:
                    team = full
                    break

        try:
            games = int(cells[1]) if cells[1].isdigit() else 0
            wins = int(cells[2]) if cells[2].isdigit() else 0
            losses = int(cells[3]) if cells[3].isdigit() else 0
            draws = int(cells[4]) if cells[4].isdigit() else 0
            pct = cells[5] if cells[5] else ".000"
            gb = cells[6] if cells[6] not in ("", "--", "---") else "—"
        except (ValueError, IndexError):
            continue

        rows.append({
            "順位": len(rows) + 1,
            "チーム": short_name(team),
            "正式名": team,
            "試合": games,
            "勝": wins,
            "敗": losses,
            "分": draws,
            "勝率": pct,
            "差": gb,
        })

    if not rows:
        return None

    df = pd.DataFrame(rows)
    # 勝率で再ソート（念のため）
    df = df.sort_values(
        by=["勝率", "勝"],
        ascending=[False, False],
        key=lambda s: s.map(lambda x: float(x) if isinstance(x, str) and x.replace(".", "").isdigit() else x)
    ).reset_index(drop=True)
    df["順位"] = range(1, len(df) + 1)
    return df


# ------------------------------------------------------------
# 順位履歴
# ------------------------------------------------------------
def load_history() -> dict:
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"CL": {}, "PL": {}}


def save_history(history: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def update_history(cl_df: Optional[pd.DataFrame], pl_df: Optional[pd.DataFrame]) -> dict:
    """現在の順位を履歴に追記して返す"""
    history = load_history()
    today = datetime.date.today().isoformat()

    for league, df in (("CL", cl_df), ("PL", pl_df)):
        if df is None or df.empty:
            continue
        if today not in history[league]:
            history[league][today] = {}
        for _, row in df.iterrows():
            history[league][today][row["正式名"]] = int(row["順位"])

    save_history(history)
    return history


def build_rank_chart(history: dict, league: str, title: str) -> go.Figure:
    """順位推移グラフを生成"""
    league_hist = history.get(league, {})
    if not league_hist:
        fig = go.Figure()
        fig.add_annotation(
            text="履歴データがまだありません<br>GitHub Actions で日次更新されると蓄積されます",
            xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False, font=dict(size=14, color="gray")
        )
        fig.update_layout(height=420, title=title)
        return fig

    dates = sorted(league_hist.keys())
    # 表示用に月日だけにする
    date_labels = [d[5:].replace("-", "/") for d in dates]  # MM/DD

    # 全チームを収集
    all_teams = set()
    for day in league_hist.values():
        all_teams.update(day.keys())

    fig = go.Figure()
    for team in sorted(all_teams, key=lambda t: TEAM_META.get(t, {}).get("short", t)):
        ranks = []
        for d in dates:
            ranks.append(league_hist[d].get(team))
        # None は前の値で埋める（途中から出現した場合）
        filled = []
        last = None
        for r in ranks:
            if r is not None:
                last = r
            filled.append(last)

        if all(v is None for v in filled):
            continue

        fig.add_trace(go.Scatter(
            x=date_labels,
            y=filled,
            mode="lines+markers",
            name=short_name(team),
            line=dict(color=team_color(team), width=2.5),
            marker=dict(size=7),
            hovertemplate="%{x}<br>%{fullData.name}: %{y}位<extra></extra>",
        ))

    fig.update_layout(
        title=title,
        yaxis=dict(
            title="順位",
            autorange="reversed",
            dtick=1,
            range=[0.5, 6.5],
            tickvals=[1, 2, 3, 4, 5, 6],
        ),
        xaxis=dict(title="日付", tickangle=-30),
        height=480,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=20, t=60, b=60),
        hovermode="x unified",
    )
    return fig


# ------------------------------------------------------------
# UI
# ------------------------------------------------------------
def style_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """表示用に列を整える"""
    return df[["順位", "チーム", "試合", "勝", "敗", "分", "勝率", "差"]]


def main():
    st.title("⚾ 2026年 プロ野球 順位表 & 推移")
    st.caption("データ出典: NPB公式サイト (npb.jp) ｜ 30分キャッシュ")

    # 順位表取得
    cl_df = fetch_standings("c")
    pl_df = fetch_standings("p")

    # 履歴更新（ローカル実行時のみ有効。Streamlit Cloud では書き込み不可の場合あり）
    try:
        history = update_history(cl_df, pl_df)
    except Exception:
        history = load_history()

    # ---- 順位表 ----
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("セントラル・リーグ")
        if cl_df is not None and not cl_df.empty:
            st.dataframe(
                style_dataframe(cl_df),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "順位": st.column_config.NumberColumn(width="small"),
                    "勝率": st.column_config.TextColumn(width="small"),
                    "差": st.column_config.TextColumn(width="small"),
                },
            )
        else:
            st.error("セ・リーグの順位表を取得できませんでした")

    with col2:
        st.subheader("パシフィック・リーグ")
        if pl_df is not None and not pl_df.empty:
            st.dataframe(
                style_dataframe(pl_df),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "順位": st.column_config.NumberColumn(width="small"),
                    "勝率": st.column_config.TextColumn(width="small"),
                    "差": st.column_config.TextColumn(width="small"),
                },
            )
        else:
            st.error("パ・リーグの順位表を取得できませんでした")

    st.divider()

    # ---- 順位推移 ----
    st.subheader("📈 順位推移")
    st.caption("GitHub Actions で毎日スナップショットを取ることで履歴が蓄積されます")

    tab1, tab2 = st.tabs(["セ・リーグ", "パ・リーグ"])

    with tab1:
        fig_cl = build_rank_chart(history, "CL", "セントラル・リーグ 順位推移")
        st.plotly_chart(fig_cl, use_container_width=True)

    with tab2:
        fig_pl = build_rank_chart(history, "PL", "パシフィック・リーグ 順位推移")
        st.plotly_chart(fig_pl, use_container_width=True)

    # ---- フッター ----
    now = datetime.datetime.now().strftime("%Y年%m月%d日 %H:%M")
    st.caption(f"最終更新: {now} ｜ キャッシュ有効期限: 30分")


if __name__ == "__main__":
    main()
