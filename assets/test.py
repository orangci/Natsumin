from globals import *

ROW_NAMES = {
	0: "Base Contract",
	1: "Challenge Contract",
	2: "Veteran Special",
	3: "Movie Special",
	4: "VN Special",
	5: "Indie Special",
	6: "Extreme Special",
	7: "Base Buddy",
	8: "Challenge Buddy"
}

def convert_sheet_to_database(sheet_data) -> dict:
	rows = sheet_data['values']

	final_data = {}

	for row in rows:
		status = row[0]
		username = row[1]
		contract_names = row[2:11]
		contract_passed = row[12:21]

		contracts = {}

		for i in range(len(contract_names)):
			row_name = ROW_NAMES[i]
			row_content = contract_names[i]

			if row_content == "-":
				continue
			passed_contract = True if len(contract_passed) > i and contract_passed[i] == "PASSED" else False
			contracts[row_name] = {"name": row_content, "passed": passed_contract}


		final_data[username.lower()] = {
			"status": "PASSED" if status == "P" else "FAILED" if status == "F" else status,
			"contracts": contracts
		}
	
	return final_data
		
with open("data.json", "r") as f:
	converted_data = convert_sheet_to_database(json.load(f))

with open("contracts.json", "w") as f:
	json.dump(converted_data, f, indent=4)