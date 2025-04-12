from typing import TypedDict
import re

class ContractData(TypedDict):
	name: str
	passed: bool
	contractor: str
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

		base_contract = cur_user_data["contracts"]["Base Contract"]
		base_contract["contractor"] = contractor
		base_contract["status"] = row[0]
		base_contract["progress"] = row[29].replace("\n", "") if len(row) > 29 and row[29] != "" else "?/?"
		base_contract["rating"] = row[26]
		base_contract["review_url"] = _get_first_url(row[31] if len(row) > 31 else "")
		base_contract["medium"] = row[9]
		if "Challenge Contract" in cur_user_data["contracts"]:
			challenge_contract = cur_user_data["contracts"]["Challenge Contract"]
			challenge_contract["contractor"] = contractor
			challenge_contract["status"] = row[1]
			challenge_contract["progress"] = row[30] if len(row) > 30 and row[30] != "" else "?/?"
			challenge_contract["rating"] = row[28]
			challenge_contract["review_url"] = _get_first_url(row[32] if len(row) > 32 else "")
			challenge_contract["medium"] = row[13]
	
	return cur_database

def _get_specials_data(cur_database: ContractsDatabase, sheet_data) -> ContractsDatabase:

	# Veteran Special Sheet
	rows: list[list[str]] = sheet_data["valueRanges"][2]["values"]

	for row in rows:
		username = row[2].lower()
		if username not in cur_database["users"]:
			continue
		cur_user_data = cur_database["users"][username]
		veteran_special = cur_user_data["contracts"]["Veteran Special"]
		veteran_special["status"] = row[5]
		veteran_special["progress"] = row[6] if len(row) > 6 and row[6] != "" else "?/?"
		veteran_special["rating"] = row[7]
		veteran_special["review_url"] = _get_first_url(row[8]) if len(row) > 8 else ""
		veteran_special["contractor"] = row[4].lower()
		veteran_special["medium"] = re.sub(CONTRACT_NAME_MEDIUM_REGEX, r"\2", row[3])
	
	# VN Special Sheet
	rows: list[list[str]] = sheet_data["valueRanges"][3]["values"]
	for row in rows:
		username = row[2].lower()
		if username not in cur_database["users"]:
			continue
		cur_user_data = cur_database["users"][username]
		vn_special = cur_user_data["contracts"]["VN Special"]
		vn_special["status"] = row[0]
		vn_special["progress"] = "Completed" if row[0] == "PASSED" else "Not Completed"
		vn_special["rating"] = row[5]
		vn_special["review_url"] = _get_first_url(row[6]) if len(row) > 6 else ""
		vn_special["contractor"] = row[4].lower()
		vn_special["medium"] = "VN"
	
	# Movie Special Sheet
	rows: list[list[str]] = sheet_data["valueRanges"][4]["values"]
	for row in rows:
		username = row[2].lower()
		if username not in cur_database["users"]:
			continue
		cur_user_data = cur_database["users"][username]
		movie_special = cur_user_data["contracts"]["Movie Special"]
		movie_special["status"] = row[0]
		movie_special["progress"] = "Completed" if row[0] == "PASSED" else "Not Completed"
		movie_special["rating"] = row[5]
		movie_special["review_url"] = _get_first_url(row[6]) if len(row) > 6 else ""
		movie_special["contractor"] = row[4].lower()
		movie_special["medium"] = "Movie"
	
	# Indie Special Sheet
	rows: list[list[str]] = sheet_data["valueRanges"][5]["values"]
	for row in rows:
		username = row[2].lower()
		if username not in cur_database["users"]:
			continue
		cur_user_data = cur_database["users"][username]
		indie_special = cur_user_data["contracts"]["Indie Special"]
		indie_special["status"] = row[0]
		indie_special["progress"] = row[5]
		indie_special["rating"] = row[6]
		indie_special["review_url"] = _get_first_url(row[7]) if len(row) > 7 else ""
		indie_special["contractor"] = row[4].lower()
		indie_special["medium"] = "Game"
	
	# Extreme Special Sheet
	rows: list[list[str]] = sheet_data["valueRanges"][6]["values"]
	for row in rows:
		username = row[2].lower()
		if username not in cur_database["users"]:
			continue
		cur_user_data = cur_database["users"][username]
		extreme_special = cur_user_data["contracts"]["Extreme Special"]
		extreme_special["status"] = row[0]
		extreme_special["progress"] = "Completed" if row[0] == "PASSED" else "Not Completed"
		extreme_special["rating"] = row[5]
		extreme_special["review_url"] = _get_first_url(row[6]) if len(row) > 6 else ""
		extreme_special["contractor"] = row[4].lower()
		extreme_special["medium"] = "Game"
	
	# Buddying Sheet
	rows: list[list[str]] = sheet_data["valueRanges"][7]["values"]
	for row in rows:
		username = row[2].lower()
		if username not in cur_database["users"]:
			continue
		
		cur_user_data = cur_database["users"][username]
		if "Base Buddy" in cur_user_data["contracts"]:
			buddy_base = cur_user_data["contracts"]["Base Buddy"]
			buddy_base["status"] = row[0]
			buddy_base["contractor"] = row[4].lower()
			buddy_base["progress"] = row[8] if row[8] != "" else "?/?"
			buddy_base["rating"] = row[10]
			buddy_base["review_url"] = _get_first_url(row[12]) if len(row) > 12 else ""
			buddy_base["medium"] = "Anime / Manga"
		if "Challenge Buddy" in cur_user_data["contracts"]:
			buddy_challenge = cur_user_data["contracts"]["Challenge Buddy"]
			buddy_challenge["status"] = row[1]
			buddy_challenge["contractor"] = row[6].lower()
			buddy_challenge["progress"] = row[9] if row[9] != "" else "?/?"
			buddy_challenge["rating"] = row[11]
			buddy_challenge["review_url"] = _get_first_url(row[13]) if len(row) > 13 else ""
			buddy_challenge["medium"] = "Anime / Manga"

	return cur_database

def convert_sheet_to_database(sheet_data) -> ContractsDatabase:
	final_database = {}
	dashboard_database = _get_dashboard_data(sheet_data) # Initial data from the dashboard
	basechallenge_database = _get_basechallenge_data(dashboard_database, sheet_data) # Base and challenge data
	specials_database = _get_specials_data(basechallenge_database, sheet_data) # Specials data

	final_database = specials_database
	return final_database