"""Fetch the 50 most recent NAVER news results for iPhone and Galaxy."""

import json
import os
import re
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
URL = "https://naverapihub.apigw.ntruss.com/search/v1/news"
QUERIES = ("아이폰", "갤럭시")


def clean(value):
    value = re.sub(r"<[^>]+>", "", value or "")
    for old, new in (("&quot;", '"'), ("&amp;", "&"), ("&#39;", "'"), ("&lt;", "<"), ("&gt;", ">")):
        value = value.replace(old, new)
    return value.strip()


def main():
    load_dotenv(ROOT / "api_keys.env")
    client_id = os.getenv("NAVER_API_HUB_CLIENT_ID", "").strip()
    client_secret = os.getenv("NAVER_API_HUB_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        raise SystemExit("api_keys.env에 인증값을 입력해 주세요.")

    headers = {
        "X-NCP-APIGW-API-KEY-ID": client_id,
        "X-NCP-APIGW-API-KEY": client_secret,
    }
    fetched_at = datetime.now().astimezone().isoformat()
    results = []
    for query in QUERIES:
        response = requests.get(
            URL,
            headers=headers,
            params={"query": query, "display": 50, "start": 1, "sort": "date", "format": "json"},
            timeout=30,
        )
        try:
            body = response.json()
        except ValueError:
            body = {"responseText": response.text[:2000]}
        if not response.ok or not isinstance(body, dict) or "items" not in body:
            raise SystemExit(f"{query} 요청 실패: HTTP {response.status_code}, 응답={json.dumps(body, ensure_ascii=False)[:600]}")
        results.append({"query": query, "status_code": response.status_code, "total": body.get("total"), "display": body.get("display"), "items": body.get("items", [])})

    stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    out = ROOT / "data" / "raw" / f"naver_news_iphone_galaxy_50_{stamp}.json"
    out.write_text(json.dumps({"collected_at": fetched_at, "sort": "date", "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")

    for group in results:
        print(f"\n## {group['query']} — 전체 {group['total']:,}건 중 최신 {len(group['items'])}건")
        for i, item in enumerate(group["items"], 1):
            print(f"{i:02d}. [{item.get('pubDate', '')}] {clean(item.get('title', ''))}")
            if item.get("description"):
                print(f"    {clean(item['description'])}")
            print(f"    {item.get('link', '')}")
    print(f"\n원본 JSON 저장: {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
