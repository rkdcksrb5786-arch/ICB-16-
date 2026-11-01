"""Query NAVER API HUB search endpoints and print a compact results table."""

import os
import re
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://naverapihub.apigw.ntruss.com"
ENDPOINTS = [
    ("뉴스", "news"),
    ("백과사전", "encyc"),
    ("블로그", "blog"),
    ("웹 문서", "webkr"),
    ("지식iN", "kin"),
    ("카페글", "cafearticle"),
    ("지역", "local"),
]


def clean(value):
    return re.sub(r"<[^>]+>", "", value or "").replace("&quot;", '"').replace("&amp;", "&").replace("&#39;", "'").strip()


def main():
    load_dotenv(ROOT / "api_keys.env")
    client_id = os.getenv("NAVER_API_HUB_CLIENT_ID", "").strip()
    client_secret = os.getenv("NAVER_API_HUB_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        raise SystemExit("api_keys.env에 인증값을 입력해 주세요.")

    headers = {"X-NCP-APIGW-API-KEY-ID": client_id, "X-NCP-APIGW-API-KEY": client_secret}
    stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    rows = []
    raw = []
    for label, endpoint in ENDPOINTS:
        params = {"query": "아이폰", "display": 5, "format": "json"}
        params["sort"] = "comment" if endpoint == "local" else "date"
        if endpoint == "local":
            params["query"] = "서울 애플스토어"
        try:
            response = requests.get(
                f"{BASE_URL}/search/v1/{endpoint}",
                headers=headers,
                params=params,
                timeout=20,
            )
            try:
                body = response.json()
            except ValueError:
                body = {}
            items = body.get("items", []) if isinstance(body, dict) else []
            title = clean(items[0].get("title", "")) if items else ""
            if response.ok and isinstance(body, dict) and isinstance(body.get("total"), int):
                rows.append((label, f"{body['total']:,}", title or "(대표 결과 없음)", response.status_code))
            else:
                error = body.get("error", body) if isinstance(body, dict) else body
                message = error.get("message", error.get("errorMessage", str(error))) if isinstance(error, dict) else str(error)
                rows.append((label, "—", f"HTTP {response.status_code}: {clean(message)[:100]}", response.status_code))
            raw.append({"api": label, "endpoint": f"/search/v1/{endpoint}", "params": params, "status_code": response.status_code, "response": body})
        except requests.RequestException as exc:
            rows.append((label, "—", f"요청 실패: {type(exc).__name__}", None))

    raw_path = ROOT / "data" / "raw" / f"naver_search_iphone_{stamp}.json"
    raw_path.write_text(__import__("json").dumps({"query": "아이폰", "collected_at": datetime.now().astimezone().isoformat(), "results": raw}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("API | 전체 결과 수 | 조회 건수 | 결과 제목 · 요약 · 메타정보")
    print("---|---:|---:|---")
    for row, result in zip(rows, raw):
        label, total, title, status = row
        items = result.get("response", {}).get("items", [])
        print(f"\n### {label} ({result.get('endpoint')}, HTTP {status}) — 검색어: {result.get('params', {}).get('query')}")
        print(f"전체 결과 수: {total}; 이번 호출에서 받은 건수: {len(items)}")
        if not items:
            print(f"오류/비고: {title}")
        for index, item in enumerate(items, 1):
            print(f"{index}. {clean(item.get('title', ''))}")
            if item.get("description"):
                print(f"   요약: {clean(item['description'])}")
            meta = [item.get(k) for k in ("postdate", "pubDate", "cafename", "category", "roadAddress") if item.get(k)]
            if meta:
                print(f"   정보: {' · '.join(meta)}")
            if item.get("link"):
                print(f"   링크: {item['link']}")
    print(f"\n원본 응답: {raw_path.relative_to(ROOT)}")
    return 0 if all(row[3] == 200 for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
