"""Extract BoW and TF-IDF keywords by brand/theme and render Korean word clouds."""

import csv
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

from kiwipiepy import Kiwi
from PIL import Image, ImageDraw, ImageFont
from sklearn.feature_extraction.text import TfidfVectorizer

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/processed/naver_news_iphone_galaxy_classified.csv"
TABLE = ROOT / "data/processed/naver_news_iphone_galaxy_keywords_bow_tfidf.csv"
FIGURES = ROOT / "outputs/figures/keyword_wordclouds"
FONT = Path(r"C:\Windows\Fonts\malgun.ttf")
BRANDS = ("아이폰", "갤럭시")
TOPICS = ("제품 출시·제품 소식", "협업", "할인·행사", "실적·사업", "기타")
STOP = set("기자 사진 영상 제공 관련 통해 위해 대한 이번 오늘 지난 최근 올해 당시 이후 국내 글로벌 한국 미국 중국 애플 삼성전자 삼성 뉴스 보도 발표 공개 출시 제품 스마트폰 아이폰 갤럭시 quot amp https www com html co kr sns".split())
STOP |= set("한다 했다 있는 있는지 것으로 것으로서 대해 통해 에서 에게 하고 되며 밝혔다 말했다 전했다 따르면 위한 경우 서비스 사용 가능 지원 적용 탑재 예정 계획 확인 분석 조사 시장 업체 사업 회사 고객 모델 시리즈 기능 신제품 스마트 삼성전자 애플 아이폰 갤럭시".split())


def tokenize(kiwi, text):
    out = []
    for token in kiwi.tokenize(re.sub(r"&(?:quot|amp|nbsp);|https?://\S+|www\.\S+", " ", text)):
        word = token.form.lower()
        if token.tag.startswith(("NNG", "NNP", "SL")) and len(word) > 1 and word not in STOP and not word.isdigit():
            out.append(word)
    return out


def draw_cloud(weighted, path, title, seed):
    width, height = 900, 620
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((30, 20), title, font=ImageFont.truetype(str(FONT), 30), fill="#222222")
    words = sorted(weighted.items(), key=lambda x: (-x[1], x[0]))[:45]
    if not words:
        draw.text((40, 100), "분석할 키워드가 없습니다", font=ImageFont.truetype(str(FONT), 28), fill="#777777")
        image.save(path)
        return
    low, high = min(v for _, v in words), max(v for _, v in words)
    placed = []
    colors = ["#145DA0", "#0C7C59", "#B23A48", "#7A5195", "#D17A00", "#245B69"]
    for rank, (word, value) in enumerate(words):
        scale = 1 if high == low else (value - low) / (high - low)
        size = int(18 + 49 * scale)
        font = ImageFont.truetype(str(FONT), size)
        box = draw.textbbox((0, 0), word, font=font)
        tw, th = box[2] - box[0], box[3] - box[1]
        found = None
        # Deterministic spiral placement, rejecting overlaps.
        phase = (seed % 17) * 0.2
        for i in range(7000):
            angle = i * 0.19 + phase
            radius = 2.7 * math.sqrt(i)
            x = int(width / 2 + radius * math.cos(angle) - tw / 2)
            y = int(height / 2 + radius * math.sin(angle) * 0.68 - th / 2 + 20)
            rect = (x - 3, y - 2, x + tw + 3, y + th + 2)
            if x < 8 or y < 65 or x + tw >= width - 8 or y + th >= height - 8:
                continue
            if all(rect[2] <= p[0] or rect[0] >= p[2] or rect[3] <= p[1] or rect[1] >= p[3] for p in placed):
                found = (x, y, rect)
                break
        if found:
            x, y, rect = found
            draw.text((x, y), word, font=font, fill=colors[rank % len(colors)])
            placed.append(rect)
    image.save(path)


def main():
    with SOURCE.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    kiwi = Kiwi()
    groups = defaultdict(list)
    for row in rows:
        text = re.sub(r"<[^>]+>", " ", f"{row['제목']} {row['요약']}")
        groups[(row["브랜드"], row["주제"])].append((row, tokenize(kiwi, text)))

    FIGURES.mkdir(parents=True, exist_ok=True)
    table_rows = []
    sheets = {b: [] for b in BRANDS}
    for brand in BRANDS:
        for ti, topic in enumerate(TOPICS):
            entries = groups[(brand, topic)]
            if not entries:
                continue
            docs = [tokens for _, tokens in entries]
            bow = Counter(t for doc in docs for t in doc)
            vectorizer = TfidfVectorizer(tokenizer=str.split, preprocessor=None, token_pattern=None, lowercase=False, norm="l2", smooth_idf=True, sublinear_tf=False)
            matrix = vectorizer.fit_transform([" ".join(d) if d else "emptytoken" for d in docs])
            terms = vectorizer.get_feature_names_out()
            scores = matrix.sum(axis=0).A1
            tfidf = {term: float(score) for term, score in zip(terms, scores)}
            top_bow = bow.most_common(25)
            top_tfidf = sorted(tfidf.items(), key=lambda x: (-x[1], x[0]))[:25]
            slug = "iphone" if brand == "아이폰" else "galaxy"
            topic_slug = {"제품 출시·제품 소식":"product", "협업":"collaboration", "할인·행사":"events", "실적·사업":"business", "기타":"other"}[topic]
            for method, weights in (("bow", dict(bow)), ("tfidf", tfidf)):
                p = FIGURES / f"{slug}-{topic_slug}-{method}.png"
                draw_cloud(weights, p, f"{brand} · {topic} · {method.upper()}", ti + (0 if brand == "아이폰" else 5))
                sheets[brand].append((topic, method, p))
            for rank in range(25):
                bterm, bcount = top_bow[rank] if rank < len(top_bow) else ("", "")
                tterm, tscore = top_tfidf[rank] if rank < len(top_tfidf) else ("", "")
                table_rows.append({"브랜드": brand, "주제": topic, "기사수": len(entries), "순위": rank + 1, "BoW_키워드": bterm, "BoW_빈도": bcount, "TF-IDF_키워드": tterm, "TF-IDF_가중치합": f"{tscore:.6f}" if tterm else ""})

    with TABLE.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["브랜드", "주제", "기사수", "순위", "BoW_키워드", "BoW_빈도", "TF-IDF_키워드", "TF-IDF_가중치합"])
        writer.writeheader(); writer.writerows(table_rows)

    # Brand contact sheets: each non-empty topic is one row, BoW at left and TF-IDF at right.
    for brand, items in sheets.items():
        slug = "iphone" if brand == "아이폰" else "galaxy"
        tile_w, tile_h = 900, 620
        nonempty_topics = [topic for topic in TOPICS if any(t == topic for t, _, _ in items)]
        sheet = Image.new("RGB", (tile_w * 2, tile_h * len(nonempty_topics)), "#eeeeee")
        for idx, topic in enumerate(nonempty_topics):
            pair = {m: p for t, m, p in items if t == topic}
            if not pair: continue
            sheet.paste(Image.open(pair["bow"]), (0, idx * tile_h))
            sheet.paste(Image.open(pair["tfidf"]), (tile_w, idx * tile_h))
        sheet.save(FIGURES / f"{slug}-comparison-sheet.png")

    print(f"records={len(rows)}; nonempty_groups={sum(bool(groups[(b,t)]) for b in BRANDS for t in TOPICS)}")
    print(f"keyword_table={TABLE}")
    print(f"figures={FIGURES}")
    for brand in BRANDS:
        for topic in TOPICS:
            entries = groups[(brand, topic)]
            if entries:
                bow = Counter(t for _, toks in entries for t in toks)
                vec = TfidfVectorizer(tokenizer=str.split, preprocessor=None, token_pattern=None, lowercase=False)
                mat = vec.fit_transform([" ".join(toks) if toks else "emptytoken" for _, toks in entries])
                tf = sorted(zip(vec.get_feature_names_out(), mat.sum(axis=0).A1), key=lambda x: -x[1])[:8]
                print(f"{brand}\t{topic}\tarticles={len(entries)}\tBoW={','.join(w for w,_ in bow.most_common(8))}\tTFIDF={','.join(w for w,_ in tf)}")


if __name__ == "__main__":
    main()
