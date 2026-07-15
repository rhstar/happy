"""
B_3_predict.py - 코스닥 보통주 전체에 위험도 산출 (교차검증 기반)

[개선 배경]
기존에는 대조군(현재 상장사 224개)을 학습에 써버려, 정작 그 기업들에 대해서는
위험도를 산출하지 못했다. 이를 해결하기 위해 학습 표본(위험군 + 대조군)에는
out-of-fold 예측(cross_val_predict)을 적용해, 자기 자신을 학습에 쓰지 않은
'정직한' 점수를 부여한다. 학습에 쓰이지 않은 나머지 상장사(예측대상)는
전체 데이터로 학습한 모델로 예측한다.

결과적으로 스팩을 제외한 코스닥 보통주 전체가 다음 중 하나로 표시된다.
  - 이미 위험 발생(실질심사 대상): 확정 위험 -> 예측 점수 대신 사유 표기
  - 그 외 전체: 위험도 점수 + 위험도 상위 백분위

[점수 산출 방식]
  - 학습 표본(features.csv, 위험군 224 + 대조군 224)
      -> StratifiedKFold 5겹 out-of-fold 확률 (source='oof')
  - 예측대상(predict_features.csv, 나머지 상장사 약 1377)
      -> 전체 학습 모델의 예측 확률 (source='full')

[백분위]
'아직 실질심사 대상이 되지 않은' 기업(대조군 OOF + 예측대상)을 하나의 모집단으로
보고 위험도 순위/백분위를 매긴다. 실질심사 대상(위험 확정)은 백분위 산정에서 제외한다.

출력
  - data/risk_ranking_all.csv          : 보통주 전체 통합 랭킹 (앱이 사용)
  - data/risk_ranking_no_embezzle.csv  : 예측대상만 (기존 하위 스크립트 호환용)

주의: OOF 점수(대조군)와 전체모델 점수(예측대상)는 각기 다른 표본 크기로 학습된
모델에서 나오므로 완전히 동일한 척도는 아니다. 동일 하이퍼파라미터/동일 분포이므로
실무적으로는 비교 가능하나, 해석 시 이 점을 감안한다.
"""
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_predict

FEATURE_COLS = ['n_shareholder_change', 'n_capital_increase', 'n_cb', 'n_collateral']


def make_model():
    return RandomForestClassifier(
        n_estimators=300, max_depth=5, min_samples_leaf=5,
        random_state=42, class_weight='balanced'
    )


def build_all_scores(model_factory=make_model):
    """보통주 전체 통합 랭킹 DataFrame을 만든다."""
    # ===== 학습 표본 (위험군 + 대조군) =====
    train = pd.read_csv("data/features.csv", dtype={'종목코드': str})
    train['종목코드'] = train['종목코드'].str.zfill(6)
    X_train = train[FEATURE_COLS]
    y_train = train['label']

    # 실질심사 사유(위험군) 병합용
    dataset = pd.read_csv("data/dataset.csv", dtype={'종목코드': str})
    dataset['종목코드'] = dataset['종목코드'].str.zfill(6)
    reason_map = dict(zip(dataset['종목코드'], dataset['실질심사사유'].fillna('')))

    # ===== 학습 표본: out-of-fold 점수 =====
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    oof = cross_val_predict(model_factory(), X_train, y_train, cv=cv,
                            method='predict_proba')[:, 1]
    train_scored = train[['회사명', '종목코드', *FEATURE_COLS, 'label']].copy()
    train_scored['risk_score'] = oof
    train_scored['source'] = 'oof'

    # ===== 예측대상: 전체 학습 모델로 예측 =====
    model = model_factory()
    model.fit(X_train, y_train)

    predict = pd.read_csv("data/predict_features.csv", dtype={'종목코드': str})
    predict['종목코드'] = predict['종목코드'].str.zfill(6)
    predict['risk_score'] = model.predict_proba(predict[FEATURE_COLS])[:, 1]
    predict['label'] = 0            # 미확정(대조군과 동일하게 '아직 아님')
    predict['source'] = 'full'
    predict_scored = predict[['회사명', '종목코드', *FEATURE_COLS,
                              'label', 'risk_score', 'source']].copy()

    # ===== 통합 =====
    allc = pd.concat([train_scored, predict_scored], ignore_index=True)
    # 혹시 모를 중복(대조군이 예측대상에 섞이는 경우) 방지: 종목코드 기준 위험군 우선
    allc = allc.sort_values('label', ascending=False).drop_duplicates('종목코드', keep='first')

    # 위험 확정 여부 = 실질심사 대상(label==1)
    allc['위험발생'] = allc['label'] == 1
    allc['실질심사사유'] = allc['종목코드'].map(reason_map).fillna('')

    # ===== 백분위: 위험 미확정(위험발생=False) 모집단 기준 =====
    pending = allc[~allc['위험발생']].copy()
    pending['순위'] = pending['risk_score'].rank(ascending=False, method='min').astype(int)
    pending['백분위'] = (pending['순위'] / len(pending) * 100).round(1)
    allc = allc.merge(pending[['종목코드', '순위', '백분위']], on='종목코드', how='left')

    allc = allc.sort_values(['위험발생', 'risk_score'], ascending=[False, False])
    return allc


if __name__ == '__main__':
    allc = build_all_scores()

    out_cols = ['회사명', '종목코드', *FEATURE_COLS, 'risk_score', 'source',
                '위험발생', '실질심사사유', '순위', '백분위']
    allc[out_cols].to_csv("data/risk_ranking_all.csv", index=False, encoding='utf-8-sig')

    # 기존 하위 스크립트(네트워크 분석/10_combine 등) 호환: 예측대상만 별도 저장
    legacy = allc[allc['source'] == 'full'][
        [*FEATURE_COLS, '종목코드', '회사명', 'risk_score']
    ].sort_values('risk_score', ascending=False)
    legacy.to_csv("data/risk_ranking_no_embezzle.csv", index=False, encoding='utf-8-sig')

    n_risky = int(allc['위험발생'].sum())
    n_pending = int((~allc['위험발생']).sum())
    print(f"통합 랭킹: {len(allc)}개 (위험확정 {n_risky} + 미확정 {n_pending})")
    print(f"  - OOF 점수(학습 표본): {(allc['source']=='oof').sum()}개")
    print(f"  - 전체모델 점수(예측대상): {(allc['source']=='full').sum()}개")

    print("\n=== 위험도 상위 15 (위험 미확정 기업 중) ===")
    top = allc[~allc['위험발생']].nlargest(15, 'risk_score').copy()
    top['위험도%'] = (top['risk_score'] * 100).round(1)
    view = top[['회사명', '종목코드', '위험도%', '백분위', 'source']]
    print(view.to_string(index=False))