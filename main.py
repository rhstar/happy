import os
from dotenv import load_dotenv
from opendartreader import OpenDartReader

load_dotenv()
api_key = os.getenv("DART_API_KEY")

dart = OpenDartReader(api_key)

'''Get-Content "C:\Users\andyr\Documents\GitHub\happy\.venv\Lib\site-packages\opendartreader\dart_event.py"
를 실행해서 dart.report
'''

# 최대주주 변동 이력 조회 (예: 삼성전자=005930, 2023년)
df = dart.report('005930',bsns_year=2023 )
# df = dart.report('005930', '최대주주변동', 2023)
print(df)

# python main.py