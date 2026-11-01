"""Collect the next 100 latest news results per brand to complete the curated set."""

import json
import os
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
URL = "https://naverapihub.apigw.ntruss.com/search/v1/news"
QUERIES = ("아이폰", "갤럭시")


def main():
    load_dotenv(ROOT / "api_keys.env")
    client_id = os.getenv("NAVER_API_HUB_CLIENT_ID", "").strip()
    client_secret = os.getenv("NAVER_API_HUB_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        raise SystemExit("api_keys.env에 인증값을 입력해 주세요.")
    headers = {"X-NCP-APIGW-API-KEY-ID": client_id, "X-NCP-APIGW-API-KEY": client_secret}
    groups = []
    for query in QUERIES:
        response = requests.get(
            URL,
            headers=headers,
            params={"query": query, "display": 100, "start": 51, "sort": "date", "format": "json"},
            timeout=30,
        )
        body = response.json()
        if not response.ok or not isinstance(body, dict) or "items" not in body:
            raise SystemExit(f"{query}: HTTP {response.status_code}; {json.dumps(body, ensure_ascii=False)[:500]}")
        groups.append({"query": query, "status_code": response.status_code, "start": 51, "display": len(body["items"]), "total": body.get("total"), "items": body["items"]})
        print(f"{query}: {len(body['items'])}건 수집 (전체 {body.get('total', 0):,}건)")
    payload = {"collected_at": datetime.now().astimezone().isoformat(), "sort": "date", "results": groups}
    stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    out = ROOT / "data" / "raw" / f"naver_news_additional_iphone_galaxy_{stamp}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"원본 저장: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
