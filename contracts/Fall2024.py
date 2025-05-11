from contracts.classes import Season, User, Contract, SeasonStats, ContractType
from async_lru import alru_cache
import aiohttp
import os
import re

CONTRACT_TYPES = [
	ContractType.BASE_CONTRACT,
	ContractType.CHALLENGE_CONTRACT,
	ContractType.VETERAN_SPECIAL,
	ContractType.TRASH_SPECIAL,
	ContractType.COMMUNITY_SPECIAL,
	ContractType.MYSTERY_SPECIAL,
	ContractType.BASE_BUDDY,
	ContractType.CHALLENGE_BUDDY,
]
OPTIONAL_CONTRACTS = []

DASHBOARD_ROW_NAMES = {
	0: ContractType.BASE_CONTRACT,
	1: ContractType.CHALLENGE_CONTRACT,
	2: ContractType.VETERAN_SPECIAL,
	3: ContractType.TRASH_SPECIAL,
	4: ContractType.COMMUNITY_SPECIAL,
	5: ContractType.MYSTERY_SPECIAL,
	6: ContractType.BASE_BUDDY,
	7: ContractType.CHALLENGE_BUDDY,
}


SPREADSHEET_ID = "1AW-1_tBIltk3GM0MJ_qe2e69pa9WpEfP0IzNRoDjhJU"

URL_REGEX = r"(https?:\/\/[^\s]+)"
CONTRACT_NAME_MEDIUM_REGEX = r"(.*) \((.*)\)"


def _get_first_url(text: str) -> str:
	match = re.search(URL_REGEX, text)
	if match:
		return match.group(0)
	return ""


def _get_season_dashboard_data(sheet_data) -> Season:
	rows: list[list[str]] = sheet_data["valueRanges"][0]["values"]

	season = Season()
	total_contracts = 0
	total_contracts_passed = 0
	users_passed = 0
	per_contract_stats: dict[str, list[int]] = {
		ContractType.BASE_CONTRACT: [0, 0],
		ContractType.CHALLENGE_CONTRACT: [0, 0],
		ContractType.VETERAN_SPECIAL: [0, 0],
		ContractType.TRASH_SPECIAL: [0, 0],
		ContractType.COMMUNITY_SPECIAL: [0, 0],
		ContractType.MYSTERY_SPECIAL: [0, 0],
		ContractType.BASE_BUDDY: [0, 0],
		ContractType.CHALLENGE_BUDDY: [0, 0],
	}

	for row in rows:
		status = row[0]
		username = row[1].strip().lower()
		contract_names = row[2:10]
		contract_passed = row[11:19]

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

			contracts[row_name] = Contract(name=row_content.replace("\n", ", "), passed=passed_contract)

		user_passed_contracts = True if status == "P" else False
		if user_passed_contracts:
			users_passed += 1

		if status == "P":
			status = "PASSED"
		elif status == "F":
			status = "FAILED"
		elif status == "LP":
			status = "LATE PASS"
		elif status == "INC":
			status = "INCOMPLETE"
		season.users[username] = User(name=username, status=status, contracts=contracts)

	season.stats = SeasonStats(
		users=len(season.users),
		users_passed=users_passed,
		contracts=total_contracts,
		contracts_passed=total_contracts_passed,
		contract_types=per_contract_stats,
	)

	return season


def _add_basechallenge_data(season: Season, sheet_data):
	rows: list[list[str]] = sheet_data["valueRanges"][1]["values"]

	for row in rows:
		username = row[3].strip().lower()
		contractor = row[5].strip().lower()

		if username not in season.users:
			continue

		user: User = season.users[username]
		rep_name = row[2].strip().upper()
		if rep_name not in season.reps:
			season.reps[rep_name] = "N/A"

		user.rep = rep_name
		user.contractor = contractor
		user.list_url = _get_first_url(row[7])
		user.veto_used = True if row[10] == "TRUE" else False
		user.preferences = row[16].replace("\n", ", ")
		user.bans = row[17].replace("\n", ", ")
		user.accepting_manhwa = True if row[18] == "Yes" else False
		user.accepting_ln = True if row[19] == "Yes" else False

		base_contract: Contract = user.contracts["Base Contract"]
		base_contract.contractor = contractor
		base_contract.status = row[0]
		base_contract.progress = row[33].replace("\n", "") if len(row) > 33 and row[33] != "" else "?/?"
		base_contract.rating = row[30]
		base_contract.review_url = _get_first_url(row[35] if len(row) > 35 else "")
		base_contract.medium = row[9]
		if "Challenge Contract" in user.contracts:
			challenge_contract: Contract = user.contracts["Challenge Contract"]
			challenge_contract.contractor = contractor
			challenge_contract.status = row[1]
			challenge_contract.progress = row[34] if len(row) > 34 and row[34] != "" else "?/?"
			challenge_contract.rating = row[32]
			challenge_contract.review_url = _get_first_url(row[36] if len(row) > 36 else "")
			challenge_contract.medium = row[13]


def _convert_sheet_to_season(sheet_data) -> Season:
	season = _get_season_dashboard_data(sheet_data)

	_add_basechallenge_data(season, sheet_data)

	return season


@alru_cache(maxsize=1)
async def get_data(session: aiohttp.ClientSession) -> Season:
	async with session.get(
		f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}/values:batchGet",
		params={
			"majorDimension": "ROWS",
			"valueRenderOption": "FORMATTED_VALUE",
			"ranges": ["Dashboard!A2:S430", "Base!A2:AK430"],
			"key": os.getenv("GOOGLE_API_KEY"),
		},
	) as response:
		response.raise_for_status()
		sheet_data = await response.json()
		return _convert_sheet_to_season(sheet_data)
