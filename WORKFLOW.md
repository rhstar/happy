# 워크플로 재구성: 수집 ↔ 분석 분리

기존 `collect_indicators.py`는 "DART 공시 수집"과 "2년치 카운트"를 한 번에 처리해서,
관찰 창을 2년→3년→5년으로 바꿀 때마다 DART API를 재호출해야 했다(느림, 15분+).

이를 **수집 단계(느림·1회)** 와 **분석 단계(빠름·반복)** 로 분리했다.

```
[수집 단계 — DART API, 한 번만, 오래 걸림]
  python collect_raw_disclosures.py     # → data/raw_disclosures.csv (5년치, long format)

[분석 단계 — API 없음, 빠름, 반복 가능]
  python aggregate_features.py 3         # N년(기본3) 창으로 집계 → features.csv / predict_features.csv
  python 3_train_model.py                # 랜덤포레스트 학습 (기존 코드 그대로)
  python 4_predict.py                    # 교차검증 기반 통합 랭킹 (기존 코드 그대로)
  # 대시보드: 통합앱.py (pages/1_조회_대시보드.py 가 risk_ranking_all.csv 사용)
```

## 새 파일

### `collect_raw_disclosures.py` (수집 단계, DART API 필요)
- 공시를 "집계 숫자"가 아니라 **공시 1건당 1줄(long format)** 로 날짜와 함께 저장.
- 수집 대상: 위험군+대조군(`dataset.csv`) + 예측대상(`predict_targets.csv`) = 약 1,839개.
- 관찰 창: 기준일(ref_date)로부터 과거 **5년** (기존 2년 → 5년으로 확장).
- 출력 `data/raw_disclosures.csv` 컬럼: `종목코드 | 회사명 | ref_date | rcept_dt | 공시유형`
  - 공시유형 ∈ {경영권변경, 유상증자, 전환사채, 담보제공} — 기존 키워드 그대로.
  - 한 제목이 여러 유형에 걸리면 유형별로 각각 한 줄(기존 유형별 독립 카운트 재현).
- **재실행 안전**: 중간에 끊겨도 이미 수집한 종목코드는 건너뛰고 이어붙인다
  (`data/raw_disclosures_completed.txt` 로 0건 기업까지 완료 추적).
- 임원 수집은 이 단계에 속하지만 이번엔 실행하지 않음(기존 CSV 재사용).

### `aggregate_features.py` (분석 단계, API 없음)
- `raw_disclosures.csv`를 읽어 **기준일 − N년** 창으로 필터해 유형별 카운트.
- `python aggregate_features.py 3` → `features_3y.csv`, `predict_features_3y.csv` 생성.
- 기본적으로 **정규 파일**(`features.csv`, `predict_features.csv`)로 승격 →
  `3_train_model.py`, `4_predict.py` 를 **수정 없이** 재사용 가능.
- 정규 파일을 덮어쓰기 전 기존본을 `data/backup/…bak` 로 백업.
- 5년판 비교: `python aggregate_features.py 5 --no-promote` → `features_5y.csv` 만 생성.

## 관찰 창 두 축 (혼동 금지)
- **지표(공시) 창**: 기본 3년 (사용자 선호). 5년도 즉시 비교 가능.
- **경영진 재직시점 창**: 3년 (네트워크 분석 축). 지표 창과 **독립 파라미터**.

## 대시보드 연결 (확인 완료)
`pages/1_조회_대시보드.py` 는 이미 `data/risk_ranking_all.csv`(통합 랭킹)를 우선 로드하고,
없으면 `risk_ranking_no_embezzle.csv` 로 폴백한다. 통합 랭킹을 쓰면 **대조군도 교차검증
점수(OOF)** 가 표시된다. 별도 수정 불필요 — `4_predict.py` 만 다시 돌리면 갱신된다.
