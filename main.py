import os
from dotenv import load_dotenv
from opendartreader import OpenDartReader

load_dotenv()
api_key = os.getenv("DART_API_KEY")

dart = OpenDartReader(api_key)

# 최대주주 변동 이력 조회 (예: 삼성전자, 2023년)
df = dart.report('005930', '최대주주변동', 2023)
print(df)

# python main.py