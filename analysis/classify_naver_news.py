"""Classify the curated news collection into primary editorial themes."""

import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/processed/naver_news_iphone_galaxy_50_each.csv"
OUTPUT = ROOT / "data/processed/naver_news_iphone_galaxy_classified.csv"


def classify(row):
    title = row["제목"].lower()
    text = f"{title} {row['요약']}".lower()

    # Promotional campaigns and retail events take priority when they are the article's main subject.
    event_terms = ("페스티벌", "할인", "특별전", "쇼핑대전", "핫딜", "판촉", "경품", "세일")
    if any(term in text for term in event_terms):
        return "할인·행사"

    if any(term in text for term in ("쇼핑라이브", "쇼핑 라이브", "캠페인 모델", "공연 결합", "협업", "콜라보")):
        return "협업"

    other_terms = (
        "부트롬", "취약점", "시드 문구", "잠금 화면", "긴급 연락처", "pass 신분증", "과학수사",
        "충전 피해야", "티머니 잔액", "cpu 설계자", "의료 정보",
    )
    if any(term in title for term in other_terms):
        return "기타"

    business_terms = (
        "시총", "실적", "매출", "영업이익", "사업", "시장", "출하", "수요", "공급", "수율", "재고",
        "원가", "메모리", "낸드", "칩플레이션", "판매", "완판", "소진", "대기", "물량", "적자",
        "증권", "비트코인", "나스닥", "코스피", "증시", "주간브리핑", "폭스콘", "하라주쿠매장", "경쟁자",
        "가격", "퀄컴 오라이언", "티머니", "저울질", "점유율", "증발", "생태계", "57년", "혁신",
        "시장 1위", "시장 20%", "삼성mx", "변신",
    )
    sales_terms = ("완판", "초도 물량", "물량 완판", "품절", "판매했다", "판매했다", "판매를", "판매량")
    if any(term in title for term in business_terms) or any(term in text for term in sales_terms):
        return "실적·사업"

    product_terms = (
        "아이폰", "iphone", "갤럭시", "폴드", "폴더블", "버즈", "워치", "링", "ios", "one ui",
        "카플레이", "a시리즈", "a20", "엑시노스", "스냅드래곤", "카메라", "화면", "힌지", "디스플레이",
        "배터리", "터치", "페이스id", "face id", "ui·ux", "사용성", "충전",
    )
    if any(term in text for term in product_terms):
        return "제품 출시·제품 소식"
    return "기타"


def main():
    with SOURCE.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        row["주제"] = classify(row)

    fields = list(rows[0].keys())
    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    counts = Counter((row["브랜드"], row["주제"]) for row in rows)
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["브랜드"], row["주제"])].append(row["제목"])
    for brand in ("아이폰", "갤럭시"):
        print(f"## {brand}")
        for topic in ("제품 출시·제품 소식", "협업", "할인·행사", "실적·사업", "기타"):
            print(f"{topic}: {counts[(brand, topic)]}")
            for title in grouped[(brand, topic)]:
                print(f"- {re.sub(r'<[^>]+>', '', title)}")
    print(f"분류 데이터: {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
