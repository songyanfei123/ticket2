import os
from datetime import datetime, timedelta
import requests
import streamlit as st
import pandas as pd

st.set_page_config(page_title="공연·콘서트 검색 대시보드", page_icon="🎫", layout="wide")

# ---------------- Styles ----------------
st.markdown("""
<style>
body { background: linear-gradient(135deg, #e0f7fa, #ffffff); font-family: 'Noto Sans KR', sans-serif; }
section.main > div { background: rgba(255,255,255,.86); padding: 1.5rem 2rem; border-radius: 14px; box-shadow: 0 4px 18px rgba(0,0,0,.06); }
h1,h2,h3 { color:#0c356a; }
.small { font-size: 0.9rem; opacity: .8; }
.card { padding: 1rem; border-radius: 12px; border: 1px solid rgba(0,0,0,.06); background: #fff; }
.card h3 { margin: .2rem 0 .6rem 0; }
.badge { display:inline-block; padding: .15rem .5rem; border-radius: 999px; background:#eef6ff; }
</style>
""", unsafe_allow_html=True)

# ---------------- On-Page Password Gate ----------------
SERVER_PW = st.secrets.get("APP_PASSWORD", os.environ.get("APP_PASSWORD", ""))

st.title("🎫 공연·콘서트 검색 대시보드")
st.caption("데이터 소스: Ticketmaster Discovery API")

if "authed" not in st.session_state:
    st.session_state.authed = False

with st.container():
    st.subheader("🔐 접근 비밀번호")
    pw = st.text_input("비밀번호를 입력하세요", type="password", help="운영자가 설정한 비밀번호입니다.")
    col_a, col_b = st.columns([1,3])
    with col_a:
        if st.button("입장하기", use_container_width=True):
            if SERVER_PW:
                if pw == SERVER_PW:
                    st.session_state.authed = True
                    st.success("인증 성공! 아래에서 공연을 검색하세요.")
                else:
                    st.error("비밀번호가 올바르지 않습니다.")
            else:
                # No server password configured — allow any non-empty password, but warn.
                if pw.strip():
                    st.session_state.authed = True
                    st.warning("서버 비밀번호가 설정되지 않아 임시로 통과했습니다. 배포 시 Secrets에 APP_PASSWORD를 설정하세요.")
                else:
                    st.error("비밀번호를 입력하세요.")

if not st.session_state.authed:
    st.stop()

# ---------------- Sidebar ----------------
with st.sidebar:
    st.title("설정")
    st.subheader("🔑 API Key")
    api_key_input = st.text_input("TICKETMASTER_KEY 입력", type="password", placeholder="Ticketmaster Discovery API key")
    st.caption("Secrets에 추가하지 않았다면 여기 입력하세요.")
    st.markdown("---")
    st.subheader("⚙️ 검색 옵션")
    default_from = datetime.utcnow().date()
    default_to = default_from + timedelta(days=14)
    city = st.text_input("도시 (예: Seoul / Tokyo / LA)", value="Seoul")
    keyword = st.text_input("키워드 (선택, 예: musical, concert)", value="")
    country = st.text_input("국가코드(선택, ISO2 예: KR/JP/US)", value="")
    size = st.select_slider("페이지 당 결과 개수", options=[10,20,30,50,100], value=20)
    page = st.number_input("페이지", min_value=0, value=0, step=1)
    from_date = st.date_input("시작일(UTC)", value=default_from)
    to_date = st.date_input("종료일(UTC)", value=default_to)

# ---------------- Ticketmaster API ----------------
TM_BASE = "https://app.ticketmaster.com/discovery/v2"
API_KEY = st.secrets.get("TICKETMASTER_KEY") or os.environ.get("TICKETMASTER_KEY") or api_key_input

def iso8601_date(d):
    return f"{d.strftime('%Y-%m-%d')}T00:00:00Z"

def tm_search_events():
    if not API_KEY:
        st.warning("⚠️ TICKETMASTER_KEY가 설정되지 않았습니다. 왼쪽에 키를 입력하거나 Secrets에 추가하세요.")
        return None
    params = {
        "apikey": API_KEY,
        "size": size,
        "page": page,
        "sort": "date,asc",
        "locale": "*",
        "city": city or None,
        "keyword": keyword or None,
        "countryCode": country or None,
        "startDateTime": iso8601_date(from_date),
        "endDateTime": iso8601_date(to_date),
    }
    params = {k: v for k, v in params.items() if v}
    try:
        r = requests.get(f"{TM_BASE}/events.json", params=params, timeout=25)
    except Exception as e:
        st.error(f"요청 실패: {e}")
        return None
    if r.status_code == 401:
        st.error("인증 실패(401): API Key를 확인하세요.")
        return None
    if r.status_code != 200:
        st.error(f"API 오류: {r.status_code} • {r.text[:200]}")
        return None
    return r.json()

def get_image(images):
    if not images: 
        return None
    images = sorted(images, key=lambda x: x.get("width", 0))
    for im in images:
        if 300 <= im.get("width", 0) <= 800:
            return im.get("url")
    return images[-1].get("url")

st.markdown("### 🔎 공연 검색")
if st.button("검색 시작하기", use_container_width=True):
    data = tm_search_events()
    if not data:
        st.warning("검색 결과가 없습니다.")
    else:
        events = data.get("_embedded", {}).get("events", [])
        total = data.get("page", {}).get("totalElements", 0)
        st.success(f"총 {total}개 중 현재 페이지에 {len(events)}개 표시 (page={page})")

        for ev in events:
            name = ev.get("name", "Untitled")
            url = ev.get("url")
            images = get_image(ev.get("images"))
            dates = ev.get("dates", {}).get("start", {})
            dt = dates.get("dateTime") or f"{dates.get('localDate','')} {dates.get('localTime','')}"
            venues = ev.get("_embedded", {}).get("venues", [])
            vname = venues[0].get("name") if venues else "—"
            vcity = venues[0].get("city", {}).get("name") if venues else ""
            vcountry = venues[0].get("country", {}).get("countryCode") if venues else ""
            price_ranges = ev.get("priceRanges",[{}])
            price = ""
            if price_ranges:
                pr = price_ranges[0]
                if pr.get("min") and pr.get("max"):
                    currency = pr.get("currency","")
                    price = f"{pr['min']}~{pr['max']} {currency}"

            with st.container():
                col1, col2 = st.columns([1,3])
                with col1:
                    if images:
                        st.image(images, use_column_width=True)
                    else:
                        st.markdown('<div class="badge">No Image</div>', unsafe_allow_html=True)
                with col2:
                    st.markdown(f"### {name}")
                    st.markdown(f"**일시(UTC/Local):** {dt or '—'}")
                    st.markdown(f"**장소:** {vname} — {vcity} {vcountry}")
                    if price:
                        st.markdown(f"**가격대:** {price}")
                    if url:
                        st.link_button("자세히 보기 ↗", url)

        # Table + download
        rows = []
        for ev in events:
            venues = ev.get("_embedded", {}).get("venues", [])
            rows.append({
                "이벤트": ev.get("name"),
                "날짜(UTC/Local)": ev.get("dates", {}).get("start", {}).get("dateTime") or f"{ev.get('dates', {}).get('start', {}).get('localDate','')} {ev.get('dates', {}).get('start', {}).get('localTime','')}",
                "장소": venues[0].get("name") if venues else "",
                "도시": venues[0].get("city", {}).get("name") if venues else "",
                "국가": venues[0].get("country", {}).get("countryCode") if venues else "",
                "링크": ev.get("url")
            })
        if rows:
            st.markdown("#### 표로 보기")
            st.dataframe(pd.DataFrame(rows), use_container_width=True)
            csv = pd.DataFrame(rows).to_csv(index=False).encode("utf-8")
            st.download_button("CSV 다운로드", csv, file_name=f"events_{city}_{keyword}.csv", mime="text/csv")

st.markdown("---")
st.caption("© 2025 Ticketmaster Discovery API • On-page password • Gradient theme: Blue-White")