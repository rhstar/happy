import os
from dotenv import load_dotenv
from opendartreader import OpenDartReader
import pandas as pd

load_dotenv()
api_key = os.getenv("DART_API_KEY")

dart = OpenDartReader(api_key)

# '''Get-Content "C:\Users\andyr\Documents\GitHub\happy\.venv\Lib\site-packages\opendartreader\dart_event.py" -Encoding UTF8
#
# 를 실행해서 dart.report에 들어가는 변수 확인
# '''


# python main.py