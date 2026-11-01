"""Interactive dashboard for the NAVER iPhone vs Galaxy analysis."""

from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data/processed"
FIG = ROOT / "outputs/figures"
BRANDS = ["아이폰", "갤럭시"]
TOPICS = ["제품 출시·제품 소식", "협업", "할인·행사", "실적·사업", "기타"]

st.set_page_config(page_title="아이폰 vs 갤럭시 | 검색·뉴스 분석", page_icon="📊", layout="wide")
st.markdown("""
<style>
  .block-container {padding-top: 1.5rem; padding-bottom: 2.5rem; max-width: 1500px;}
  .hero {padding: 1.4rem 1.6rem; border-radius: 16px; background: linear-gradient(120deg,#eef5ff,#f7f4ff); margin-bottom: 1rem;}
  .hero p {color:#5d6675; margin-bottom:0;}
  div[data-testid="stMetric"] {background:#fafbfc; border:1px solid #e8ebf0; padding:14px 16px; border-radius:12px;}
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_data():
    news = pd.read_csv(DATA / "naver_news_iphone_galaxy_classified.csv", encoding="utf-8-sig")
    keywords = pd.read_csv(DATA / "naver_news_iphone_galaxy_keywords_bow_tfidf.csv", encoding="utf-8-sig")
    trends = pd.read_csv(DATA / "naver_search_trend_brands_monthly.csv", encoding="utf-8-sig", parse_dates=["period"])
    age_summary = pd.read_csv(DATA / "naver_search_trend_brands_age_summary.csv", encoding="utf-8-sig")
    annual = pd.read_csv(DATA / "naver_search_trend_brands_annual_summary.csv", encoding="utf-8-sig")
    return news, keywords, trends, age_summary, annual


try:
    news, keywords, trends, age_summary, annual = load_data()
except Exception as exc:
    st.error(f"분석 자료를 불러오지 못했습니다: {exc}")
    st.stop()

st.markdown("<div class='hero'><h1>아이폰 vs 갤럭시</h1><p>네이버 뉴스 100건과 네이버 통합검색 관심도 기반 경쟁사 분석</p></div>", unsafe_allow_html=True)
page = st.radio("분석 메뉴", ["한눈에 보기", "뉴스 분석", "검색 추이", "키워드 분석"], horizontal=True, label_visibility="collapsed")

if page == "한눈에 보기":
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("분석 뉴스", f"{len(news):,}건", "브랜드별 50건")
    c2.metric("검색 추이", "60개월", "2021.11–2026.10")
    c3.metric("분석 연령대", "7개", "0–12세 ~ 60세 이상")
    c4.metric("분류 주제", "5개", "출시·협업·행사·사업·기타")
    left, right = st.columns([1.1, 1])
    with left:
        st.subheader("검색 관심도 월별 추이")
        st.image(str(FIG / "search_trends/brand-monthly-overall.png"), use_container_width=True)
    with right:
        st.subheader("최근 12개월 연령별 관심도")
        st.dataframe(age_summary[["연령대", "아이폰_상대비율", "갤럭시_상대비율"]], hide_index=True, use_container_width=True,
                     column_config={"아이폰_상대비율": st.column_config.NumberColumn("아이폰 (연령대 내 상대)", format="%.1f"), "갤럭시_상대비율": st.column_config.NumberColumn("갤럭시 (연령대 내 상대)", format="%.1f")})
        st.caption("각 연령대 안에서 두 브랜드의 최근 12개월 평균지수를 그 연령대의 높은 브랜드를 100으로 환산했습니다. 연령대끼리는 직접 비교할 수 없습니다.")
    st.subheader("주제별 뉴스 건수")
    counts = news.groupby(["주제", "브랜드"]).size().unstack(fill_value=0).reindex(TOPICS)
    st.bar_chart(counts)
    st.info("검색 추이는 실제 검색량이나 시장점유율이 아닌 네이버 검색 관심도 상대지수입니다. 급등 시점은 제품 출시 일정 등과 함께 살펴보세요.")

elif page == "뉴스 분석":
    st.subheader("브랜드별 뉴스")
    f1, f2, f3 = st.columns([1, 1.2, 2])
    brand_sel = f1.multiselect("브랜드", BRANDS, default=BRANDS)
    topic_sel = f2.multiselect("주제", TOPICS, default=TOPICS)
    query = f3.text_input("제목·요약 검색", placeholder="예: 폴더블, 할인, 실적")
    filtered = news[news["브랜드"].isin(brand_sel) & news["주제"].isin(topic_sel)].copy()
    if query:
        filtered = filtered[filtered["제목"].str.contains(query, case=False, na=False) | filtered["요약"].str.contains(query, case=False, na=False)]
    st.caption(f"필터 결과 {len(filtered):,}건")
    st.dataframe(filtered[["브랜드", "주제", "날짜", "제목", "요약", "원문링크"]], hide_index=True, use_container_width=True, height=580,
                 column_config={"원문링크": st.column_config.LinkColumn("원문 링크", display_text="기사 열기"), "요약": st.column_config.TextColumn("요약", width="large"), "제목": st.column_config.TextColumn("제목", width="large")})
    st.download_button("현재 결과 CSV 다운로드", filtered.to_csv(index=False).encode("utf-8-sig"), "filtered_news.csv", "text/csv")

elif page == "검색 추이":
    st.subheader("월별 검색 관심도")
    trends_view = trends[trends["age_group"] == "전체"].pivot(index="period", columns="brand", values="ratio").sort_index()
    st.line_chart(trends_view, height=380)
    means = trends[trends["age_group"] == "전체"].groupby("brand")["ratio"].mean()
    a, b, c = st.columns(3)
    a.metric("기간", "2021.11–2026.10", "60개월")
    b.metric("아이폰 평균 상대지수", f"{means.get('아이폰', 0):.1f}")
    c.metric("갤럭시 평균 상대지수", f"{means.get('갤럭시', 0):.1f}")
    st.divider()
    age_groups = [x for x in trends["age_group"].drop_duplicates().tolist() if x != "전체"]
    age = st.selectbox("연령대 선택", age_groups, index=0)
    age_view = trends[trends["age_group"] == age].pivot(index="period", columns="brand", values="ratio").sort_index()
    st.line_chart(age_view, height=360)
    st.image(str(FIG / "search_trends/brand-monthly-by-age.png"), caption="전체 연령대 월별 추이 비교", use_container_width=True)
    st.warning("검색어 트렌드는 네이버 통합검색 상대지수입니다. 연령대별 시계열은 각 연령 조건 안에서 브랜드 간 비교에 사용하며, 서로 다른 연령대의 지수 크기를 직접 비교하지 마세요.")
    st.download_button("검색 추이 CSV 다운로드", trends.to_csv(index=False).encode("utf-8-sig"), "search_trends.csv", "text/csv")

else:
    st.subheader("BoW와 TF-IDF 키워드 비교")
    k1, k2, k3 = st.columns(3)
    brand = k1.selectbox("브랜드", BRANDS)
    available_topics = keywords.loc[keywords["브랜드"] == brand, "주제"].drop_duplicates().tolist()
    topic = k2.selectbox("주제", available_topics)
    method = k3.radio("워드클라우드", ["BoW", "TF-IDF"], horizontal=True)
    slug = "iphone" if brand == "아이폰" else "galaxy"
    topic_slug = {"제품 출시·제품 소식":"product", "협업":"collaboration", "할인·행사":"events", "실적·사업":"business", "기타":"other"}[topic]
    method_slug = "bow" if method == "BoW" else "tfidf"
    image_path = FIG / "keyword_wordclouds" / f"{slug}-{topic_slug}-{method_slug}.png"
    left, right = st.columns([1.05, 1])
    with left:
        st.image(str(image_path), use_container_width=True)
    with right:
        st.markdown(f"**{brand} · {topic}**")
        view = keywords[(keywords["브랜드"] == brand) & (keywords["주제"] == topic)].copy()
        st.dataframe(view[["순위", "BoW_키워드", "BoW_빈도", "TF-IDF_키워드", "TF-IDF_가중치합"]], hide_index=True, use_container_width=True, height=560)
    st.caption("BoW는 기사군에서의 단어 빈도, TF-IDF는 기사별 가중치 합입니다. 브랜드명과 일반 뉴스 표현 등 불용어를 제외한 명사·영문 토큰 중심 분석입니다.")
    compare = st.selectbox("같은 조합의 BoW·TF-IDF 비교 시트", ["비교 시트 보기"])
    sheet = FIG / "keyword_wordclouds" / f"{slug}-comparison-sheet.png"
    st.image(str(sheet), use_container_width=True)

st.caption("자료: NAVER API HUB 검색어 트렌드 및 뉴스 검색 결과 · 프로젝트 분석 자료")
