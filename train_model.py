import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.inspection import permutation_importance

# ===== 1. 데이터 로드 =====
features = pd.read_csv("data/features.csv")

# 사용할 지표 5개 (불성실공시 제외)->features의 지표를 분석했을 때 불성실 공시가 위험대상 지표에 포함되어 있지 않아 변수로서 가치를 상실함
FEATURE_COLS = [
    'n_shareholder_change',
    'n_capital_increase',
    'n_cb',
    'n_collateral',
    'has_embezzle',
]

X = features[FEATURE_COLS]   # 입력: 5개 지표
y = features['label']        # 정답: 위험(1)/대조군(0)

print(f"학습 데이터: {len(X)}개, 지표 {len(FEATURE_COLS)}개")
print(f"위험 {(y==1).sum()}개 / 대조군 {(y==0).sum()}개\n")

# ===== 2. 모델 정의 =====
model = RandomForestClassifier(
    n_estimators=300,      # 나무 300개
    max_depth=5,           # 과적합 억제: 나무 깊이 제한
    min_samples_leaf=5,    # 과적합 억제: 잎사귀 최소 표본
    random_state=42,       # 재현성
    class_weight='balanced'
)

# ===== 3. 교차검증으로 성능 평가 =====
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
scores = cross_val_score(model, X, y, cv=cv, scoring='roc_auc')

print("=== 5-Fold 교차검증 (ROC-AUC) ===")
print(f"각 fold: {scores.round(3)}")
print(f"평균: {scores.mean():.3f} (±{scores.std():.3f})")


# 전체 데이터로 모델 학습 (importance 추출용)
model.fit(X, y)

# --- 1. MDI (기본 importance) ---
mdi = pd.Series(model.feature_importances_, index=FEATURE_COLS).sort_values(ascending=False)
print("=== MDI Feature Importance ===")
print(mdi.round(3))

# --- 2. Permutation importance ---
perm = permutation_importance(model, X, y, n_repeats=30, random_state=42, scoring='roc_auc')
perm_series = pd.Series(perm.importances_mean, index=FEATURE_COLS).sort_values(ascending=False)
print("\n=== Permutation Importance ===")
print(perm_series.round(3))