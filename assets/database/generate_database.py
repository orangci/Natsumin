#from globals import *
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from contracts_database import *
import json

with open("assets/database/data.json", "r", encoding="utf8") as f:
	converted_data = convert_sheet_to_database(json.load(f))

with open("assets/database/database.json", "w") as f:
	json.dump(converted_data, f, indent=4)