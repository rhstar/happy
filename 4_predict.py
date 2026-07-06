import pandas as pd
from sklearn.ensemble import RandomForestClassifier

# ===== 4개 지표 모델 학습 (횡령 제외) =====
train = pd.read_csv("data/features.csv")
FEATURE_COLS = ['n_shareholder_change', 'n_capital_increase', 'n_cb', 'n_collateral']

X_train = train[FEATURE_COLS]
y_train = train['label']

model = RandomForestClassifier(
    n_estimators=300, max_depth=5, min_samples_leaf=5,
    random_state=42, class_weight='balanced'
)
model.fit(X_train, y_train)

# ===== 현재 상장사 예측 =====
predict = pd.read_csv("data/predict_features.csv", dtype={'종목코드': str})
predict['종목코드'] = predict['종목코드'].str.zfill(6)

X_predict = predict[FEATURE_COLS]
predict['risk_score'] = model.predict_proba(X_predict)[:, 1]

ranked = predict.sort_values('risk_score', ascending=False)
ranked.to_csv("data/risk_ranking_no_embezzle.csv", index=False, encoding='utf-8-sig')

# ===== 상위 15개 출력 =====
print("=== 조기경보 위험 상위 15개 (실질심사 기반, 4개 지표) ===\n")
top15 = ranked.head(15).copy()
top15['위험도%'] = (top15['risk_score'] * 100).round(1)
display = top15[['회사명', '종목코드', '위험도%',
                 'n_shareholder_change', 'n_capital_increase', 'n_cb', 'n_collateral']]
display.columns = ['회사명', '종목코드', '위험도%', '경영권', '유증', 'CB', '담보']
print(display.to_string(index=False))