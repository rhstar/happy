import os
from dotenv import load_dotenv
from opendartreader import OpenDartReader

load_dotenv()
api_key = os.getenv("DART_API_KEY")

dart = OpenDartReader(api_key)

company_info = dart.company('삼성전자')
print(company_info)