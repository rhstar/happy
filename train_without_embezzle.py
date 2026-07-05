import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.inspection import permutation_importance

features = pd.read_csv("data/features.csv")

# 횡령 제외한 4개 지표
FEATURE_COLS = [
    'n_shareholder_change',
    'n_capital_increase',
    'n_cb',
    'n_collateral',
]

X = features[FEATURE_COLS]
y = features['label']

model = RandomForestClassifier(
    n_estimators=300, max_depth=5, min_samples_leaf=5,
    random_state=42, class_weight='balanced'
)

# 성능 평가
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
scores = cross_val_score(model, X, y, cv=cv, scoring='roc_auc')
print("=== 횡령 제외 모델 (4개 지표) ===")
print(f"ROC-AUC: {scores.mean():.3f} (±{scores.std():.3f})")

# Feature importance
model.fit(X, y)
mdi = pd.Series(model.feature_importances_, index=FEATURE_COLS).sort_values(ascending=False)
perm = permutation_importance(model, X, y, n_repeats=30, random_state=42, scoring='roc_auc')
perm_s = pd.Series(perm.importances_mean, index=FEATURE_COLS).sort_values(ascending=False)

print("\nMDI:")
print(mdi.round(3))
print("\nPermutation:")
print(perm_s.round(3))