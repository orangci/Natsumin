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

def convert_sheet_to_database(sheet_data) -> ContractsDatabase:
	rows = sheet_data['values']

	final_data = {
		"users": {}
	}
	total_contracts = 0
	total_contracts_passed = 0
	users_passed = 0
	per_contract_stats: dict[str, list[int]] = {
		"Base Contract": [0, 0],
		"Challenge Contract": [0, 0],
		"Veteran Special": [0, 0],
		"Movie Special": [0, 0],
		"VN Special": [0, 0],
		"Indie Special": [0, 0],
		"Extreme Special": [0, 0],
		"Base Buddy": [0, 0],
		"Challenge Buddy": [0, 0]
	}

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

			total_contracts += 1
			per_contract_stats[row_name][1] += 1
			passed_contract = True if len(contract_passed) > i and contract_passed[i] == "PASSED" else False
			if passed_contract:
				total_contracts_passed += 1
				per_contract_stats[row_name][0] += 1

			contracts[row_name] = {"name": row_content, "passed": passed_contract}

		user_passed_contracts = True if status == "P" else False
		if user_passed_contracts:
			users_passed += 1

		final_data["users"][username.lower()] = {
			"status": "PASSED" if status == "P" else "FAILED" if status == "F" else status,
			"contracts": contracts
		}
	
	final_data["stats"] = {
		"users": len(final_data["users"]),
		"users_passed": users_passed,
		"contracts": total_contracts,
		"contracts_passed": total_contracts_passed,
		"contract_types": per_contract_stats
	}
	
	return final_data
		
with open("data.json", "r") as f:
	converted_data = convert_sheet_to_database(json.load(f))

with open("contracts.json", "w") as f:
	json.dump(converted_data, f, indent=4)