from typing import TypedDict
import re

class ContractData(TypedDict):
	name: str
	passed: bool
	status: str
	progress: str
	rating: str
	review_url: str
	medium: str

class ContractsUser(TypedDict):
	status: str
	rep: str
	contractor: str
	contractee: str
	list_url: str
	veto_used: bool
	accepting_manhwa: bool
	accepting_ln: bool
	preferences: str
	bans: str
	contracts: dict[str, ContractData]

class ContractsStats(TypedDict):
	users: int
	users_passed: int
	contracts: int
	contracts_passed: int
	contract_types: dict[str, list[int]]

class ContractsDatabase(TypedDict):
	users: dict[str, ContractsUser]
	stats: ContractsStats

DASHBOARD_ROW_NAMES = {
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

def _get_dashboard_data(sheet_data) -> ContractsDatabase:
	rows: list[list[str]] = sheet_data["valueRanges"][0]["values"]

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
			row_name = DASHBOARD_ROW_NAMES[i]
			row_content = contract_names[i]

			if row_content == "-":
				continue

			total_contracts += 1
			per_contract_stats[row_name][1] += 1
			passed_contract = True if len(contract_passed) > i and contract_passed[i] == "PASSED" else False
			if passed_contract:
				total_contracts_passed += 1
				per_contract_stats[row_name][0] += 1

			contracts[row_name] = {"name": row_content.replace("\n", ", "), "passed": passed_contract}

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

CONTRACT_NAME_MEDIUM_REGEX = r"(.*) \((.*)\)"
URL_REGEX = r"(https?:\/\/[^\s]+)"

def _get_first_url(text: str) -> str:
	match = re.search(URL_REGEX, text)
	if match:
		return match.group(0)
	return ""

def _get_basechallenge_data(cur_database: ContractsDatabase, sheet_data) -> ContractsDatabase:
	rows: list[list[str]] = sheet_data["valueRanges"][1]["values"]

	for row in rows:
		username = row[3].lower()
		contractor = row[5].lower()

		if username not in cur_database["users"]:
			continue

		cur_user_data = cur_database["users"][username]
		cur_user_data["rep"] = row[2]
		cur_user_data["contractor"] = contractor
		cur_user_data["list_url"] = _get_first_url(row[7])
		cur_user_data["veto_used"] = True if row[10] == "TRUE" else False
		cur_user_data["preferences"] = row[16].replace("\n", ", ")
		cur_user_data["bans"] = row[17].replace("\n", ", ")
		cur_user_data["accepting_manhwa"] = True if row[18] == "Yes" else False
		cur_user_data["accepting_ln"] = True if row[19] == "Yes" else False

		cur_user_data["contracts"]["Base Contract"]["status"] = row[0]
		cur_user_data["contracts"]["Base Contract"]["progress"] = row[29].replace("\n", "") if len(row) > 29 else "0/0"
		cur_user_data["contracts"]["Base Contract"]["rating"] = row[26]
		cur_user_data["contracts"]["Base Contract"]["review_url"] = _get_first_url(row[31] if len(row) > 31 else "")
		cur_user_data["contracts"]["Base Contract"]["medium"] = row[9]
		if "Challenge Contract" in cur_user_data["contracts"]:
			cur_user_data["contracts"]["Challenge Contract"]["status"] = row[1]
			cur_user_data["contracts"]["Challenge Contract"]["progress"] = row[30] if len(row) > 30 else "0/0"
			cur_user_data["contracts"]["Challenge Contract"]["rating"] = row[28]
			cur_user_data["contracts"]["Challenge Contract"]["review_url"] = _get_first_url(row[32] if len(row) > 32 else "")
			cur_user_data["contracts"]["Challenge Contract"]["medium"] = row[13]
	
	return cur_database

def convert_sheet_to_database(sheet_data) -> ContractsDatabase:
	final_database = {}
	dashboard_database = _get_dashboard_data(sheet_data) # Initial data from the dashboard
	basechallenge_database = _get_basechallenge_data(dashboard_database, sheet_data) # Base and challenge data

	final_database = basechallenge_database
	return final_database