import pandas as pd
from sklearn.ensemble import RandomForestClassifier

# ===== 1. 학습 데이터로 모델 훈련 =====
train = pd.read_csv("data/features.csv")
FEATURE_COLS = ['n_shareholder_change', 'n_capital_increase', 'n_cb', 'n_collateral', 'has_embezzle']

X_train = train[FEATURE_COLS]
y_train = train['label']

model = RandomForestClassifier(
    n_estimators=300, max_depth=5, min_samples_leaf=5,
    random_state=42, class_weight='balanced'
)
model.fit(X_train, y_train)

# ===== 2. 예측 대상 로드 및 위험 점수 예측 =====
predict = pd.read_csv("data/predict_features.csv", dtype={'종목코드': str})
predict['종목코드'] = predict['종목코드'].str.zfill(6)

X_predict = predict[FEATURE_COLS]
# 위험(class 1)일 확률 = 위험 점수
predict['risk_score'] = model.predict_proba(X_predict)[:, 1]

# ===== 3. 위험 점수 높은 순 정렬 =====
ranked = predict.sort_values('risk_score', ascending=False)

# 결과 저장
ranked.to_csv("data/risk_ranking.csv", index=False, encoding='utf-8-sig')

# ===== 4. 상위 15개 출력 =====
print("=== 무자본 M&A 위험 패턴 상위 15개 기업 ===\n")
cols = ['회사명', '종목코드', 'risk_score'] + FEATURE_COLS
print(ranked[cols].head(15).to_string(index=False))

# 횡령이 아직 발생하지 않은 기업만 필터링
no_embezzle = ranked[ranked['has_embezzle'] == 0].copy()

print("=" * 70)
print("  횡령 미발생 + 위험 패턴 상위 15개 (조기 경보 대상)")
print("=" * 70)

cols = ['회사명', '종목코드', 'risk_score',
        'n_shareholder_change', 'n_capital_increase', 'n_cb', 'n_collateral']
top15_early = no_embezzle[cols].head(15).copy()
top15_early['risk_score'] = (top15_early['risk_score'] * 100).round(1)
top15_early.columns = ['회사명', '종목코드', '위험도%', '경영권', '유증', 'CB', '담보']
print(top15_early.to_string(index=False))