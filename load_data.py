import pandas as pd
import os

DATA_DIR = "data"

import pandas as pd


def load_kind_html(filename):
    """KIND에서 다운로드한 HTML 위장 xls 파일을 읽는다"""
    tables = pd.read_html(f"data/{filename}", encoding='euc-kr')
    return tables[0]


if __name__ == '__main__':
    files = {
        "불성실공시": "불성실공시법인.xls",
        "상장폐지": "상장폐지현황.xls",
        "횡령": "코스닥_횡령.xls",
    }

    for label, fname in files.items():
        print(f"\n{'='*40}")
        print(f"=== {label} ({fname}) ===")
        try:
            df = load_kind_html(fname)
            print(f"행 수: {len(df)}")
            print(f"컬럼: {list(df.columns)}")
            print(df.head(3))
        except Exception as e:
            print(f"[읽기 실패] {e}")


import pandas as pd