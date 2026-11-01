"""Collect NAVER DataLab trend indices and chart brand search-interest patterns."""

import csv
import json
import os
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://naverapihub.apigw.ntruss.com/search-trend/v1/search"
START, END = "2021-11-01", "2026-10-31"
TERMS = [("아이폰", ["아이폰"]), ("갤럭시", ["갤럭시"])]
AGES = [
    ("0-12세", ["1"]), ("13-18세", ["2"]), ("19-29세", ["3", "4"]),
    ("30-39세", ["5", "6"]), ("40-49세", ["7", "8"]),
    ("50-59세", ["9", "10"]), ("60세 이상", ["11"]),
]
FONT = Path(r"C:\Windows\Fonts\malgun.ttf")
COLORS = {"아이폰": "#1769aa", "갤럭시": "#d44a3a"}


def request(headers, age_codes=None):
    body = {"startDate": START, "endDate": END, "timeUnit": "month",
            "keywordGroups": [{"groupName": name, "keywords": keywords} for name, keywords in TERMS]}
    if age_codes is not None:
        body["ages"] = age_codes
    response = requests.post(BASE_URL, headers=headers, json=body, timeout=30)
    response.raise_for_status()
    result = response.json()
    if not isinstance(result.get("results"), list) or len(result["results"]) != 2:
        raise RuntimeError("검색어 트렌드 응답에 두 브랜드 결과가 모두 없습니다.")
    return body, result


def chart_lines(series, path, title, subtitle=""):
    w, h = 1500, 850
    img = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(img)
    title_font = ImageFont.truetype(str(FONT), 36)
    font = ImageFont.truetype(str(FONT), 22)
    small = ImageFont.truetype(str(FONT), 16)
    d.text((100, 30), title, font=title_font, fill="#222")
    if subtitle: d.text((100, 80), subtitle, font=small, fill="#555")
    x0, y0, x1, y1 = 110, 150, 1430, 730
    for tick in range(0, 101, 20):
        y = y1 - (y1-y0)*tick/100
        d.line((x0,y,x1,y), fill="#e6e6e6", width=1)
        d.text((55,y-12), str(tick), font=small, fill="#555")
    d.line((x0,y0,x0,y1), fill="#555", width=2); d.line((x0,y1,x1,y1), fill="#555", width=2)
    all_periods = sorted({p for vals in series.values() for p,_ in vals})
    if not all_periods: return img.save(path)
    index = {p:i for i,p in enumerate(all_periods)}
    for brand, vals in series.items():
        pts=[]
        for period, val in vals:
            x=x0+(x1-x0)*index[period]/max(1,len(all_periods)-1)
            y=y1-(y1-y0)*float(val)/100
            pts.append((x,y))
        if len(pts)>1: d.line(pts, fill=COLORS[brand], width=4)
        for x,y in pts: d.ellipse((x-3,y-3,x+3,y+3), fill=COLORS[brand])
    # Mark yearly positions.
    shown=set()
    for i,p in enumerate(all_periods):
        year=p[:4]
        if year not in shown and (i==0 or p[5:7]=="01"):
            x=x0+(x1-x0)*i/max(1,len(all_periods)-1)
            d.text((x-25,y1+12),year,font=small,fill="#555"); shown.add(year)
    lx,ly=115,115
    for brand in series:
        d.line((lx,ly,lx+35,ly),fill=COLORS[brand],width=4); d.text((lx+44,ly-13),brand,font=font,fill="#222"); lx+=200
    img.save(path)


def main():
    load_dotenv(ROOT / "api_keys.env")
    client_id=os.getenv("NAVER_API_HUB_CLIENT_ID","").strip()
    client_secret=os.getenv("NAVER_API_HUB_CLIENT_SECRET","").strip()
    if not client_id or not client_secret: raise SystemExit("api_keys.env에 NAVER API 인증값을 입력해 주세요.")
    headers={"X-NCP-APIGW-API-KEY-ID":client_id,"X-NCP-APIGW-API-KEY":client_secret,"Content-Type":"application/json"}
    stamp=datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    rawdir=ROOT/"data/raw"; rawdir.mkdir(parents=True,exist_ok=True)
    raw={"collected_at":datetime.now().astimezone().isoformat(),"endpoint":"/search-trend/v1/search","date_range":[START,END],"timeUnit":"month","requests":[]}
    all_rows=[]
    for age_name, age_codes in [("전체",None)]+AGES:
        body,result=request(headers,age_codes)
        raw["requests"].append({"age_group":age_name,"request":body,"response":result})
        for group in result["results"]:
            for point in group.get("data",[]):
                all_rows.append({"age_group":age_name,"brand":group["title"],"keyword_terms":"|".join(group.get("keywords",[])),"period":point["period"],"ratio":point["ratio"]})
    rawpath=rawdir/f"naver_search_trend_brands_{stamp}.json"
    rawpath.write_text(json.dumps(raw,ensure_ascii=False,indent=2),encoding="utf-8")
    out=ROOT/"data/processed/naver_search_trend_brands_monthly.csv"
    with out.open("w",encoding="utf-8-sig",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=["age_group","brand","keyword_terms","period","ratio"]);writer.writeheader();writer.writerows(all_rows)
    # Compact comparable summaries. Both brands are always requested together, so their
    # ratios share a common reference within each request; age cohorts are separate requests.
    overall_rows=[r for r in all_rows if r["age_group"]=="전체"]
    annual=[]
    for year in sorted({r["period"][:4] for r in overall_rows}):
        for brand,_ in TERMS:
            vals=[float(r["ratio"]) for r in overall_rows if r["period"].startswith(year) and r["brand"]==brand]
            annual.append({"연도":year,"브랜드":brand,"월수":len(vals),"평균상대지수":f"{sum(vals)/len(vals):.2f}"})
    with (ROOT/"data/processed/naver_search_trend_brands_annual_summary.csv").open("w",encoding="utf-8-sig",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=["연도","브랜드","월수","평균상대지수"]);writer.writeheader();writer.writerows(annual)
    age_summary=[]
    recent_periods=sorted({r["period"][:7] for r in overall_rows})[-12:]
    for age_name,_ in AGES:
        means={}
        for brand,_ in TERMS:
            vals=[float(r["ratio"]) for r in all_rows if r["age_group"]==age_name and r["brand"]==brand and r["period"][:7] in recent_periods]
            means[brand]=sum(vals)/len(vals) if vals else 0
        peak=max(means.values()) or 1
        age_summary.append({"연령대":age_name,"집계월수":len(recent_periods),"아이폰_최근12개월평균지수":f"{means['아이폰']:.2f}","갤럭시_최근12개월평균지수":f"{means['갤럭시']:.2f}","아이폰_상대비율":f"{means['아이폰']/peak*100:.1f}","갤럭시_상대비율":f"{means['갤럭시']/peak*100:.1f}","해석주의":"연령대별 API 정규화 기준이 달라 연령대 간 직접 비교 금지"})
    with (ROOT/"data/processed/naver_search_trend_brands_age_summary.csv").open("w",encoding="utf-8-sig",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(age_summary[0]));writer.writeheader();writer.writerows(age_summary)
    figdir=ROOT/"outputs/figures/search_trends";figdir.mkdir(parents=True,exist_ok=True)
    overall={b:[(r["period"],r["ratio"]) for r in all_rows if r["age_group"]=="전체" and r["brand"]==b] for b,_ in TERMS}
    chart_lines(overall,figdir/"brand-monthly-overall.png","네이버 통합검색 관심도 월별 추이","각 브랜드의 기간 내 최고 월을 100으로 둔 상대지수 · 절대 검색량 아님")
    # Age small multiples; the two lines are each independently normalized in a given cohort.
    cellw,cellh=750,425
    sheet=Image.new("RGB",(cellw*2,cellh*4),"#eeeeee")
    for i,(age_name,_) in enumerate(AGES):
        series={b:[(r["period"],r["ratio"]) for r in all_rows if r["age_group"]==age_name and r["brand"]==b] for b,_ in TERMS}
        tile=Image.new("RGB",(1500,850),"white")
        # Reuse the chart renderer and scale to sheet tile.
        tmp=figdir/".age-tmp.png"; chart_lines(series,tmp,f"연령별 월간 검색 관심도 · {age_name}","각 브랜드별 해당 연령대 최고 월=100; 연령 간 절대 규모 비교 불가")
        tile=Image.open(tmp).resize((cellw,cellh));sheet.paste(tile,((i%2)*cellw,(i//2)*cellh))
    (figdir/".age-tmp.png").unlink(missing_ok=True)
    sheet.save(figdir/"brand-monthly-by-age.png")
    print(f"rows={len(all_rows)}; monthly_periods={len({r['period'] for r in all_rows if r['age_group']=='전체'})}; age_groups={len(AGES)}")
    print(f"raw={rawpath}\nprocessed={out}\nfigures={figdir}")
    for brand,_ in TERMS:
        values=[float(r["ratio"]) for r in all_rows if r["age_group"]=="전체" and r["brand"]==brand]
        peak=max((r for r in all_rows if r["age_group"]=="전체" and r["brand"]==brand),key=lambda r:float(r["ratio"]))
        print(f"{brand}: peak={peak['period']} ratio={float(peak['ratio']):.1f}; mean_index={sum(values)/len(values):.1f}")
    for age_name,_ in AGES:
        peaks=[]
        for brand,_ in TERMS:
            rs=[r for r in all_rows if r["age_group"]==age_name and r["brand"]==brand]
            if rs:
                peak=max(rs,key=lambda r:float(r["ratio"]));peaks.append(f"{brand}:{peak['period']}({float(peak['ratio']):.0f})")
        print(age_name+" "+" ".join(peaks))


if __name__=="__main__": main()
