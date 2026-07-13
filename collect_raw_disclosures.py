# -*- coding: utf-8 -*-
"""
collect_raw_disclosures.py  ── [수집 단계] 공시 원자료 5년치 long format 수집

[설계 의도]
기존 collect_indicators.py는 "공시 수집"과 "2년치 카운트"를 한 번에 처리했다.
그래서 관찰 창을 2년→3년→5년으로 바꾸려면 매번 DART API를 재호출해야 했다(느림).

이 스크립트는 공시를 '집계된 숫자'가 아니라 '공시 한 건당 한 줄(long format)'로,
날짜(rcept_dt)와 함께 넉넉히 5년치 저장한다. 이후 aggregate_features.py가
API 재호출 없이 원하는 창(3년·5년 등)으로 즉시 집계할 수 있다.

[중요]
- 이 단계만 DART API를 호출한다(오래 걸림, 기업당 0.4초 · 약 1,839개 → 15분+).
- 임원 수집 코드는 이 '수집 단계'에 속하지만, 이번에는 실행하지 않는다.
  (이미 뽑아둔 network_analysis/data/network_executives_all.csv,
   data/current_executives.csv 를 그대로 사용)
- 관찰 창 = 기준일(ref_date)로부터 과거 5년 (기존 2년 → 5년으로 확장).
- 기준일(ref_date): 위험군/대조군은 dataset.csv의 값(사유발생일 기반),
  예측대상은 predict_targets.csv의 값(2026-07-05).
- 재실행 안전(resume): 중간에 끊겨도 이미 수집한 종목코드는 건너뛰고 이어붙인다.

[출력]  data/raw_disclosures.csv  (long format)
  컬럼: 종목코드 | 회사명 | ref_date(기준일) | rcept_dt(공시일자) | 공시유형
  공시유형 ∈ {경영권변경, 유상증자, 전환사채, 담보제공}
  한 공시 제목이 여러 유형에 해당하면 유형별로 각각 한 줄씩 기록한다
  (기존 collect_indicators의 유형별 독립 카운트를 그대로 재현하기 위함).
"""
import os
import time
import pandas as pd
from dotenv import load_dotenv
from opendartreader import OpenDartReader

# ── 절대경로 하드코딩 금지: 스크립트 위치 기준으로 ROOT 자동 계산 ──
ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")

load_dotenv(os.path.join(ROOT, ".env"))
dart = OpenDartReader(os.getenv("DART_API_KEY"))

# 관찰 창(년). 넉넉히 5년치를 원자료로 수집한다.
COLLECT_YEARS = 5

# 공시유형 매칭 규칙 (기존 collect_indicators.py의 키워드를 그대로 재사용)
#   각 (유형, 매칭함수). 한 제목이 여러 유형에 걸리면 유형별로 각각 기록.
KEYWORD_RULES = [
    ("경영권변경", lambda t: ("최대주주변경" in t) or ("경영권변경" in t)),
    ("유상증자",   lambda t: "유상증자" in t),
    ("전환사채",   lambda t: "전환사채" in t),
    ("담보제공",   lambda t: "담보제공계약" in t),
]

RAW_PATH = os.path.join(DATA, "raw_disclosures.csv")
OUT_COLS = ["종목코드", "회사명", "ref_date", "rcept_dt", "공시유형"]


def load_targets():
    """수집 대상 = 위험군 + 대조군(dataset.csv) + 예측대상(predict_targets.csv).

    반환: 종목코드 · 회사명 · ref_date 를 가진 DataFrame(종목코드 유일).
    """
    ds = pd.read_csv(os.path.join(DATA, "dataset.csv"), dtype={"종목코드": str})
    ds["종목코드"] = ds["종목코드"].str.zfill(6)
    ds = ds[["회사명", "종목코드", "ref_date"]]

    pt = pd.read_csv(os.path.join(DATA, "predict_targets.csv"), dtype={"종목코드": str})
    pt["종목코드"] = pt["종목코드"].str.zfill(6)
    pt = pt[["회사명", "종목코드", "ref_date"]]

    targets = pd.concat([ds, pt], ignore_index=True)
    # 혹시 학습표본과 예측대상에 같은 코드가 있으면 학습표본(먼저 온 것) 우선
    targets = targets.drop_duplicates(subset=["종목코드"], keep="first").reset_index(drop=True)
    return targets


def collect_one(corp_code, ref_date):
    """한 기업의 5년치 공시를 long format 행 리스트로 반환."""
    ref = pd.to_datetime(ref_date)
    start = (ref - pd.DateOffset(years=COLLECT_YEARS)).strftime("%Y-%m-%d")
    end = ref.strftime("%Y-%m-%d")

    rows = []
    try:
        disc = dart.list(corp_code, start=start, end=end, kind="")
    except Exception as e:
        print(f"  [공시조회 실패] {corp_code}: {e}")
        return rows, False  # 실패 → 완료로 기록하지 않음(다음 실행 때 재시도)

    if disc is None or len(disc) == 0:
        return rows, True   # 정상 조회했으나 공시 없음 → 완료 처리(0건)

    for _, d in disc.iterrows():
        title = str(d.get("report_nm") or "")
        rcept = str(d.get("rcept_dt") or "")
        for dtype, match in KEYWORD_RULES:
            if match(title):
                rows.append({
                    "종목코드": corp_code,
                    "회사명": None,      # 호출부에서 채움
                    "ref_date": pd.to_datetime(ref_date).strftime("%Y-%m-%d"),
                    "rcept_dt": rcept,
                    "공시유형": dtype,
                })
    return rows, True


def done_codes():
    """이미 수집 완료된 종목코드 집합(resume용)."""
    if not os.path.exists(RAW_PATH):
        return set()
    try:
        prev = pd.read_csv(RAW_PATH, dtype={"종목코드": str})
        if "종목코드" not in prev.columns:
            return set()
        return set(prev["종목코드"].str.zfill(6).unique())
    except Exception:
        return set()


def main():
    os.makedirs(DATA, exist_ok=True)
    targets = load_targets()
    already = done_codes()

    # 재실행 안전: 완료 코드는 건너뛴다. (공시 0건 기업은 아래 로그로 별도 기록)
    completed_log = os.path.join(DATA, "raw_disclosures_completed.txt")
    logged_done = set()
    if os.path.exists(completed_log):
        with open(completed_log, encoding="utf-8") as f:
            logged_done = {ln.strip() for ln in f if ln.strip()}
    already = already | logged_done

    header_needed = not os.path.exists(RAW_PATH)
    total = len(targets)
    print(f"수집 대상 {total}개 · 이미 완료 {len(already)}개 · 남은 {total - len(already)}개")
    print(f"관찰 창: 기준일 - {COLLECT_YEARS}년  →  {RAW_PATH}")

    processed = 0
    for i, row in targets.iterrows():
        code = row["종목코드"]
        name = row["회사명"]
        if code in already:
            continue

        rows, ok = collect_one(code, row["ref_date"])
        for r in rows:
            r["회사명"] = name

        # 공시가 있으면 CSV에 append, 없어도 완료 로그에 남겨 재수집 방지
        if rows:
            df = pd.DataFrame(rows, columns=OUT_COLS)
            df.to_csv(RAW_PATH, mode="a", header=header_needed,
                      index=False, encoding="utf-8-sig")
            header_needed = False
        if ok:
            with open(completed_log, "a", encoding="utf-8") as f:
                f.write(code + "\n")

        processed += 1
        if processed % 20 == 0:
            print(f"진행: {processed} 처리 (누적 완료 {len(already) + processed}/{total})")
        time.sleep(0.4)

    print(f"\n완료! 원자료 → {RAW_PATH}")
    if os.path.exists(RAW_PATH):
        final = pd.read_csv(RAW_PATH, dtype={"종목코드": str})
        print(f"총 {len(final)}행 · 유형별 분포:")
        print(final["공시유형"].value_counts())


if __name__ == "__main__":
    main()
