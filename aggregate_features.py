# -*- coding: utf-8 -*-
"""
aggregate_features.py  ── [분석 단계] 원자료에서 N년 창으로 지표 집계 (API 없음)

raw_disclosures.csv(공시 1건당 1줄, 5년치)를 읽어, 기준일(ref_date)로부터
과거 N년 이내 공시만 필터해 유형별로 카운트한다. DART API를 다시 호출하지 않으므로
3년·5년 등 원하는 창을 즉시 생성·비교할 수 있다.

[출력]  (기존 3_train_model.py / 4_predict.py 와 100% 동일한 형식·컬럼명)
  - data/features_{N}y.csv          : 학습표본(위험군+대조군) 지표 + label
  - data/predict_features_{N}y.csv  : 예측대상 지표 (label 없음)
  그리고 기본적으로 아래 '정규 파일'로도 승격(promote)한다(기존 파일은 백업 후 덮어씀):
  - data/features.csv, data/predict_features.csv
    → 3_train_model.py, 4_predict.py 를 수정 없이 그대로 재사용 가능

[사용법]
  python aggregate_features.py            # 기본 3년 창 + 정규 파일 승격
  python aggregate_features.py 5          # 5년 창
  python aggregate_features.py 3 --no-promote   # features_3y.csv 만 만들고 정규파일은 유지

[주의]
  · 지표(공시) 관찰 창과 경영진 재직시점 창은 서로 다른 축의 독립 파라미터다. 혼동 금지.
  · 정규 파일(features.csv 등)을 덮어쓰기 전, 기존 파일을 data/backup/ 에 타임스탬프로 보관한다.
"""
import os
import sys
import shutil
import time
import argparse
import pandas as pd

# ── 절대경로 하드코딩 금지: 스크립트 위치 기준 ROOT 자동 계산 ──
ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")
RAW_PATH = os.path.join(DATA, "raw_disclosures.csv")

# 공시유형 → features 컬럼명 매핑
TYPE_TO_COL = {
    "경영권변경": "n_shareholder_change",
    "유상증자":   "n_capital_increase",
    "전환사채":   "n_cb",
    "담보제공":   "n_collateral",
}
FEATURE_COLS = ["n_shareholder_change", "n_capital_increase", "n_cb", "n_collateral"]


def _counts_within_window(years):
    """raw_disclosures를 N년 창으로 필터해 종목코드별 유형 카운트 DataFrame 반환."""
    raw = pd.read_csv(RAW_PATH, dtype={"종목코드": str})
    raw["종목코드"] = raw["종목코드"].str.zfill(6)
    raw["ref_date"] = pd.to_datetime(raw["ref_date"], errors="coerce")
    # rcept_dt는 YYYYMMDD 문자열 → 날짜
    raw["rcept_dt"] = pd.to_datetime(raw["rcept_dt"].astype(str).str.zfill(8),
                                     format="%Y%m%d", errors="coerce")
    raw = raw.dropna(subset=["ref_date", "rcept_dt"])

    # 기준일 - N년  ≤  공시일  ≤  기준일  (DateOffset로 정확히 'N년 전')
    start = raw["ref_date"].apply(lambda d: d - pd.DateOffset(years=years))
    mask = (raw["rcept_dt"] >= start) & (raw["rcept_dt"] <= raw["ref_date"])
    win = raw[mask].copy()

    win["col"] = win["공시유형"].map(TYPE_TO_COL)
    win = win.dropna(subset=["col"])

    counts = (win.groupby(["종목코드", "col"]).size()
                 .unstack(fill_value=0)
                 .reindex(columns=FEATURE_COLS, fill_value=0))
    return counts.astype(int)


def _build(frame_codes, counts):
    """회사명·종목코드(·label) 프레임에 카운트를 left-join, 없으면 0."""
    out = frame_codes.copy()
    out["종목코드"] = out["종목코드"].str.zfill(6)
    out = out.merge(counts, left_on="종목코드", right_index=True, how="left")
    for c in FEATURE_COLS:
        if c not in out.columns:
            out[c] = 0
        out[c] = out[c].fillna(0).astype(int)
    return out


def _backup(path):
    if os.path.exists(path):
        bdir = os.path.join(DATA, "backup")
        os.makedirs(bdir, exist_ok=True)
        stamp = time.strftime("%Y%m%d_%H%M%S")
        base = os.path.basename(path)
        dst = os.path.join(bdir, f"{base}.{stamp}.bak")
        shutil.copy2(path, dst)
        print(f"  백업: {base} → backup/{os.path.basename(dst)}")


def aggregate(years=3, promote=True):
    if not os.path.exists(RAW_PATH):
        sys.exit(f"[에러] {RAW_PATH} 가 없습니다. 먼저 collect_raw_disclosures.py 를 실행하세요.")

    counts = _counts_within_window(years)

    # ── 학습표본(features): dataset.csv 기준(회사명·종목코드·label) ──
    ds = pd.read_csv(os.path.join(DATA, "dataset.csv"), dtype={"종목코드": str})
    ds["종목코드"] = ds["종목코드"].str.zfill(6)
    feat = _build(ds[["회사명", "종목코드", "label"]], counts)
    feat = feat[FEATURE_COLS + ["종목코드", "회사명", "label"]]  # 기존 컬럼 순서

    # ── 예측대상(predict_features): predict_targets.csv 기준(회사명·종목코드) ──
    pt = pd.read_csv(os.path.join(DATA, "predict_targets.csv"), dtype={"종목코드": str})
    pt["종목코드"] = pt["종목코드"].str.zfill(6)
    pfeat = _build(pt[["회사명", "종목코드"]], counts)
    pfeat = pfeat[FEATURE_COLS + ["종목코드", "회사명"]]  # 기존 컬럼 순서(label 없음)

    # ── 창별 산출물 저장(새 파일명) ──
    fpath = os.path.join(DATA, f"features_{years}y.csv")
    ppath = os.path.join(DATA, f"predict_features_{years}y.csv")
    feat.to_csv(fpath, index=False, encoding="utf-8-sig")
    pfeat.to_csv(ppath, index=False, encoding="utf-8-sig")
    print(f"[{years}년 창] {os.path.basename(fpath)} ({len(feat)}행), "
          f"{os.path.basename(ppath)} ({len(pfeat)}행)")

    # ── 정규 파일 승격(백업 후 덮어씀) ──
    if promote:
        can_f = os.path.join(DATA, "features.csv")
        can_p = os.path.join(DATA, "predict_features.csv")
        _backup(can_f)
        _backup(can_p)
        feat.to_csv(can_f, index=False, encoding="utf-8-sig")
        pfeat.to_csv(can_p, index=False, encoding="utf-8-sig")
        print(f"  승격: features.csv / predict_features.csv 를 {years}년 창으로 갱신")
        print("  → 이제 3_train_model.py, 4_predict.py 를 그대로 실행하면 됩니다.")

    # ── 요약 ──
    print("\n[학습표본 유형별 평균]")
    print(feat.groupby('label')[FEATURE_COLS].mean().round(2).to_string())
    return feat, pfeat


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="raw_disclosures → N년 창 features 집계")
    ap.add_argument("years", nargs="?", type=int, default=3,
                    help="관찰 창(년). 기본 3")
    ap.add_argument("--no-promote", action="store_true",
                    help="정규 파일(features.csv 등)을 덮어쓰지 않음")
    args = ap.parse_args()
    aggregate(years=args.years, promote=not args.no_promote)
