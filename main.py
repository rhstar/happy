import os
from dotenv import load_dotenv
from opendartreader import OpenDartReader
import pandas as pd

load_dotenv()
api_key = os.getenv("DART_API_KEY")

dart = OpenDartReader(api_key)