"""Deduplicate and filter the collected iPhone/Galaxy news dataset."""

import csv
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/raw/naver_news_iphone_galaxy_50_20261101_103841.json"
ADDITIONAL_SOURCE = ROOT / "data/raw/naver_news_additional_iphone_galaxy_20261101_105520.json"
OUTPUT = ROOT / "data/processed/naver_news_iphone_galaxy_50_each.csv"
EXCLUSIONS = ROOT / "data/processed/naver_news_exclusions.csv"

# Manually reviewed, directly relevant additions from API ranks 51–150.
ADDITIONAL_PICKS = {
    "아이폰": (52, 56, 62, 71, 75, 83, 99, 115, 123, 125),
    "갤럭시": (71, 78, 81, 83, 90, 92, 97, 99, 100, 107, 108, 109, 111, 112, 113, 117, 119, 121, 122, 124, 131, 133, 136, 137, 138),
}

# Rank is the one-based position returned by the search API for each query.
EXCLUDE = {
    "아이폰": {
        8: "원문 링크가 갤럭시 #22와 중복이며 해당 기사는 Galaxy A18 중심이라 갤럭시에 보존",
        18: "원문 링크가 갤럭시 #28과 중복이며 제목·내용이 Galaxy Z Fold 중심이라 갤럭시에 보존",
        23: "아이폰 단축어가 본문 요약에만 잠깐 언급된 AI 에이전트 기사",
        25: "원문 링크가 갤럭시 #34와 중복이며 제목의 중심 제품이 Galaxy S26 Ultra라 갤럭시에 보존",
        26: "아이폰 디자이너 경력이 잠깐 언급된 AI 기기 기사; 갤럭시 #35와 중복 링크도 있어 양쪽 제외",
        27: "아이폰이 사진 설명에만 언급된 시가총액 기사",
        28: "아이폰이 경품으로만 언급된 중국 소비 기사",
        29: "다른 앱 X의 장애 해결 절차에서 iPhone이 플랫폼 예시로만 등장",
        31: "한국 인터넷 역사에서 아이폰을 시기 설명으로만 언급",
        37: "아이폰을 일반적 사례로만 언급한 정치·사회 칼럼",
    },
    "갤럭시": {
        1: "기아 자동차 할인 행사; Galaxy는 경품으로만 언급",
        3: "현대차·기아 할인 행사; Galaxy는 경품으로만 언급",
        4: "자동차 판촉 기사; Galaxy는 경품으로만 언급",
        5: "유통 할인 행사 모음 기사; Galaxy 제품은 여러 상품 중 하나로만 등장",
        6: "Galaxy Digital/Research 가상자산 투자사 기사로 삼성 제품과 무관",
        7: "기아 자동차 행사 기사; Galaxy는 경품으로만 언급",
        10: "기아 자동차 판촉 기사; Galaxy는 경품으로만 언급",
        11: "현대차·기아 자동차 행사; Galaxy는 경품으로만 언급",
        12: "기아 자동차 판촉 기사; Galaxy는 경품으로만 언급",
        13: "기아 신차·중고차 할인 기사; Galaxy는 경품으로만 언급",
        14: "로봇·UFO 기사에 폴드 루머가 부수적으로 삽입됨",
        16: "기아 자동차 행사 기사; Galaxy는 경품으로만 언급",
        20: "원문 링크가 아이폰 #7과 중복; 같은 기사 한 건만 유지",
        25: "원문 링크가 아이폰 #13과 중복; 비교 기사 한 건만 유지",
        26: "Galaxy Corporation 소속사 관련 기사로 삼성 제품과 무관",
        27: "Galaxy Research 가상자산 담보대출 기사로 삼성 제품과 무관",
        29: "가상자산 브리핑에서 Galaxy 기기를 결제 기능 호환 대상으로만 언급",
        30: "원문 링크가 아이폰 #24와 중복; iPhone 리뷰 한 건만 유지",
        32: "가상자산 결제 기사에서 Galaxy 기기를 호환 단말기로만 언급",
        35: "원문 링크가 아이폰 #26과 중복이며 스마트폰이 아닌 AI 기기 기사",
        44: "LA Galaxy 축구팀 경기 기사로 삼성 제품과 무관",
        45: "Galaxy라는 명칭의 삼성전기 홍보 영상 기사로 Galaxy 단말과 무관",
        48: "삼성전자 성과급 갈등 기사; Galaxy 단말은 사업 실적 맥락에서만 언급",
        49: "Galaxy Digital 가상자산 투자사 기사로 삼성 제품과 무관",
        50: "원문 링크가 아이폰 #34와 중복; iPhone 서비스 대응 기사 한 건만 유지",
    },
}


def clean(value):
    return re.sub(r"<[^>]+>", "", value or "")


def main():
    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    additional = json.loads(ADDITIONAL_SOURCE.read_text(encoding="utf-8"))
    kept = []
    removed = []
    seen_urls = set()
    for group in payload["results"]:
        brand = group["query"]
        for rank, item in enumerate(group["items"], start=1):
            url = item.get("originallink") or item.get("link") or ""
            reason = EXCLUDE.get(brand, {}).get(rank)
            if not reason and url in seen_urls:
                reason = "원문 링크가 다른 검색어 결과와 중복; 앞서 보존한 관련성이 더 높은 행만 유지"
            row = {
                "브랜드": brand,
                "제목": clean(item.get("title")),
                "요약": clean(item.get("description")),
                "날짜": item.get("pubDate", ""),
                "원문링크": url,
            }
            if reason:
                removed.append({"검색어순위": rank, **row, "제외사유": reason})
                continue
            seen_urls.add(url)
            kept.append(row)

    for group in additional["results"]:
        brand = group["query"]
        for rank, item in enumerate(group["items"], start=group["start"]):
            if rank not in ADDITIONAL_PICKS[brand]:
                continue
            url = item.get("originallink") or item.get("link") or ""
            if url in seen_urls:
                raise ValueError(f"선정한 추가 기사 URL이 기존 데이터와 중복됩니다: {brand} #{rank}")
            seen_urls.add(url)
            kept.append({
                "브랜드": brand,
                "제목": clean(item.get("title")),
                "요약": clean(item.get("description")),
                "날짜": item.get("pubDate", ""),
                "원문링크": url,
            })

    brand_order = {"아이폰": 0, "갤럭시": 1}
    # Keep brands in a stable order and newest articles first within each brand.
    kept.sort(key=lambda row: (brand_order[row["브랜드"]], -datetime.strptime(row["날짜"], "%a, %d %b %Y %H:%M:%S %z").timestamp()))

    fields = ["브랜드", "제목", "요약", "날짜", "원문링크"]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(kept)
    with EXCLUSIONS.open("w", encoding="utf-8-sig", newline="") as f:
        fields = ["브랜드", "검색어순위", "제목", "요약", "날짜", "원문링크", "제외사유"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(removed)

    print(f"최초 조회: {sum(len(g['items']) for g in payload['results'])}건")
    print(f"추가 조회: {sum(len(ADDITIONAL_PICKS[g['query']]) for g in additional['results'])}건 채택")
    print(f"필터 후: {len(kept)}건")
    print(f"제외: {len(removed)}건")
    for brand in ("아이폰", "갤럭시"):
        print(f"{brand}: {sum(r['브랜드'] == brand for r in kept)}건 유지")
    print(f"정리 데이터: {OUTPUT.relative_to(ROOT)}")
    print(f"제외 내역: {EXCLUSIONS.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
