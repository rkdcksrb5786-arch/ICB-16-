"""Run one representative NAVER API HUB request for each API family."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://naverapihub.apigw.ntruss.com"
TIMEOUT_SECONDS = 20


def main() -> int:
    load_dotenv(ROOT / "api_keys.env")
    import os

    client_id = os.getenv("NAVER_API_HUB_CLIENT_ID", "").strip()
    client_secret = os.getenv("NAVER_API_HUB_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        print("인증값이 비어 있습니다. api_keys.env를 확인해 주세요.")
        return 2

    headers = {
        "X-NCP-APIGW-API-KEY-ID": client_id,
        "X-NCP-APIGW-API-KEY": client_secret,
    }
    stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    raw_dir = ROOT / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    checks = [
        (
            "search_news",
            "GET",
            "/search/v1/news",
            {"params": {"query": "네이버 API", "display": 2, "sort": "date"}},
        ),
        (
            "search_trend",
            "POST",
            "/search-trend/v1/search",
            {
                "json": {
                    "startDate": "2025-10-01",
                    "endDate": "2025-10-31",
                    "timeUnit": "month",
                    "keywordGroups": [
                        {"groupName": "네이버", "keywords": ["네이버"]},
                        {"groupName": "인공지능", "keywords": ["인공지능", "AI"]},
                        {"groupName": "아이폰", "keywords": ["아이폰"]},
                    ],
                }
            },
        ),
        (
            "shopping_categories",
            "POST",
            "/shopping/v1/categories",
            {
                "json": {
                    "startDate": "2025-10-01",
                    "endDate": "2025-10-31",
                    "timeUnit": "month",
                    "category": [
                        {"name": "패션의류", "param": ["50000000"]},
                        {"name": "화장품/미용", "param": ["50000002"]},
                    ],
                }
            },
        ),
    ]

    failures = 0
    for name, method, path, kwargs in checks:
        request_headers = dict(headers)
        if method == "POST":
            request_headers["Content-Type"] = "application/json"
        try:
            response = requests.request(
                method,
                BASE_URL + path,
                headers=request_headers,
                timeout=TIMEOUT_SECONDS,
                **kwargs,
            )
            try:
                body = response.json()
            except ValueError:
                body = {"responseText": response.text[:2000]}
            raw_path = raw_dir / f"naver_api_{name}_{stamp}.json"
            raw_path.write_text(
                json.dumps(
                    {
                        "collected_at": datetime.now().astimezone().isoformat(),
                        "method": method,
                        "endpoint": path,
                        "status_code": response.status_code,
                        "response": body,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            ok = response.ok and isinstance(body, dict) and not (
                "error" in body or "errorCode" in body or "errMsg" in body
            )
            if ok:
                if name == "search_news":
                    detail = f"총 {body.get('total', 0)}건, 응답 {len(body.get('items', []))}건"
                else:
                    detail = f"결과 그룹 {len(body.get('results', []))}개"
                print(f"{name}: 성공 (HTTP {response.status_code}, {detail}); 원본 {raw_path.relative_to(ROOT)}")
                if name == "search_trend":
                    for group in body.get("results", []):
                        print(f"  {group.get('title', '(제목 없음)')}: 검색어={', '.join(group.get('keywords', []))}")
                        for point in group.get("data", []):
                            print(f"    {point.get('period')}: {point.get('ratio')}")
            else:
                failures += 1
                # API error messages are returned, but request headers and credentials are never printed.
                error = body.get("error", body) if isinstance(body, dict) else body
                print(f"{name}: 실패 (HTTP {response.status_code}); 응답={json.dumps(error, ensure_ascii=False)[:500]}; 원본 {raw_path.relative_to(ROOT)}")
        except requests.RequestException as exc:
            failures += 1
            print(f"{name}: 요청 실패 ({type(exc).__name__}: {str(exc)[:300]})")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
