import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import plotly.graph_objects as go
import datetime

st.set_page_config(page_title="NPB順位", layout="wide")
st.title("🧢 2026年 プロ野球 順位表 & 推移")

@st.cache_data(ttl=3600)
def get_standings(url):
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        data = []
        for tr in soup.find_all("tr"):
            tds = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            if len(tds) >= 7 and any(x.isdigit() for x in "".join(tds[:3])):
                data.append(tds[:8])
        return data
    except:
        return None

col1, col2 = st.columns(2)

with col1:
    st.subheader("セントラル・リーグ")
    data = get_standings("https://npb.jp/bis/2026/stats/std_c.html")
    if data:
        df = pd.DataFrame(data[1:7], columns=["順位","チーム","試合","勝","敗","分","勝率","差"])
        st.dataframe(df, use_container_width=True, hide_index=True)

with col2:
    st.subheader("パシフィック・リーグ")
    data = get_standings("https://npb.jp/bis/2026/stats/std_p.html")
    if data:
        df = pd.DataFrame(data[1:7], columns=["順位","チーム","試合","勝","敗","分","勝率","差"])
        st.dataframe(df, use_container_width=True, hide_index=True)

st.divider()
st.subheader("📈 開幕からの順位推移")

weeks = ["開幕", "4月上", "4月中", "4月下", "5月上", "現在"]

tab1, tab2 = st.tabs(["セ・リーグ", "パ・リーグ"])

with tab1:
    fig = go.Figure()
    for team, ranks in {"ヤクルト":[5,4,3,2,1,1], "阪神":[2,1,1,1,2,2], "巨人":[1,2,2,3,3,3], "DeNA":[3,3,4,4,4,4]}.items():
        fig.add_trace(go.Scatter(x=weeks, y=ranks, mode='lines+markers', name=team))
    fig.update_layout(yaxis=dict(autorange="reversed"), height=500)
    st.plotly_chart(fig, use_container_width=True)

st.caption(f"最終更新: {datetime.datetime.now().strftime('%Y年%m月%d日 %H:%M')}")