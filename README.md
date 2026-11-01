# 아이폰 vs 갤럭시 검색·뉴스 분석 대시보드

네이버 뉴스 검색 결과와 네이버 통합검색 관심도 자료를 브랜드별로 살펴보는 Streamlit 대시보드입니다.

## 구성

- `app.py`: 대시보드 진입 파일
- `data/processed/`: 정제 뉴스, 주제 분류, BoW·TF-IDF 키워드, 월별·연령별 검색 추이
- `outputs/figures/`: 검색 추이와 키워드 워드클라우드 이미지
- `analysis/`: 수집·정제·분석 재현용 Python 스크립트
- `data/raw/`: NAVER API 원본 응답

대시보드는 저장된 CSV와 그림을 사용합니다. 배포 실행에는 네이버 API 키가 필요하지 않습니다. API 키 파일(`api_keys.env`)은 저장소에 포함하지 않습니다.

## 로컬 실행

Python 3.12 환경에서 프로젝트 루트로 이동해 실행합니다.

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

macOS/Linux:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Streamlit Community Cloud 배포

1. Streamlit Community Cloud에서 **Create app**을 선택합니다.
2. 저장소 `rkdcksrb5786-arch/ICB-16-`와 브랜치 `main`을 선택합니다.
3. Main file path에 `app.py`를 입력합니다.
4. Advanced settings에서 Python 3.12를 선택해 배포합니다.

앱은 루트의 `requirements.txt`에서 의존성을 설치하고, 프로젝트 내 상대 경로로 데이터와 그림을 불러옵니다. 데이터 파일이나 그림을 이동할 때는 `app.py`의 경로 참조도 함께 수정해야 합니다.

## 지표 해석

- 검색 추이는 실제 검색 횟수나 시장점유율이 아닌 네이버 데이터랩 상대지수입니다.
- 같은 검색 요청에서 받은 브랜드 지수는 기간별 움직임과 상대적 관심도 비교에 사용합니다.
- 연령대별 요청은 각각 별도로 정규화되므로 서로 다른 연령대의 지수 크기를 직접 비교하지 않습니다.
- 2021년과 2026년 연도별 평균은 각각 11–12월, 1–10월 부분 기간입니다.
- 뉴스 주제는 제목과 요약을 바탕으로 5개 주요 주제로 분류했습니다.

## 데이터 기준

검색 관심도는 2021년 11월부터 2026년 10월까지 월별 자료입니다. 뉴스 분석은 정제 기준을 통과한 아이폰 50건과 갤럭시 50건을 사용합니다. 마지막 수집 시각과 원응답은 `data/raw/`에 남아 있습니다.
