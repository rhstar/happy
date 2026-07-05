import pandas as pd
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)

features = pd.read_csv("data/features.csv")
print(features.groupby('label')[
    ['n_shareholder_change', 'n_capital_increase', 'n_cb',
     'n_collateral', 'has_unfaithful', 'has_embezzle']
].mean().round(2))