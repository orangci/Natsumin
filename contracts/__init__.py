import datetime
import logging
import os
import re
import httpx
from mezmorize import Cache
from typing import Optional
from dataclasses import dataclass, field
from config import CONSOLE_LOGGING_FORMATTER, FILE_LOGGING_FORMATTER

@dataclass
class Contract:
	name: str = field()
	passed: bool = field(default=False, repr=False)
	contractor: str = field(default="", repr=False)
	status: str = field(default="")
	progress: str = field(default="?/?", repr=False)
	rating: str = field(default="0/10")
	review_url: str = field(default="", repr=False)
	medium: str = field(default="", repr=False)

@dataclass
class User:
	name: str = field()
	status: str = field(default="", repr=False)
	rep: str = field(default="")
	contractor: str = field(default="", repr=False)
	list_url: str = field(default="", repr=False)
	veto_used: bool = field(default=False, repr=False)
	accepting_manhwa: bool = field(default=False, repr=False)
	accepting_ln: bool = field(default=False, repr=False)
	preferences: str = field(default="", repr=False)
	bans: str = field(default="", repr=False)
	contracts: dict[str, Contract] = field(default_factory=dict, repr=False)

	def get_contractor(self, season: "Season") -> Optional["User"]:
		return season.get_user(self.contractor)

	def get_contractee(self, season: "Season") -> Optional["User"]:
		users_with_this_contractor = [user for user in season.users.values() if user.contractor == self.name]
		return users_with_this_contractor[0] if len(users_with_this_contractor) > 0 else None		

@dataclass
class SeasonStats:
	users_passed: int = -1
	users: int = -1
	contracts_passed: int = -1
	contracts: int = -1
	contract_types: dict[str, list[int]] = field(default_factory=dict, repr=False)

@dataclass
class Season:
	users: dict[str, User] = field(default_factory=dict, repr=False)
	stats: SeasonStats = None

	def get_user(self, username: str) -> Optional["User"]:
		return self.users.get(username, None)

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
URL_REGEX = r"(https?:\/\/[^\s]+)"
CONTRACT_NAME_MEDIUM_REGEX = r"(.*) \((.*)\)"

SPREADSHEET_ID = "19aueoNx6BBU6amX7DhKGU8kHVauHWcSGiGKMzFSGkGc"
GET_SHEET_DATA_URL = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}/values:batchGet"
#SHEET_DATA_CACHE_DURATION = 1

season_sheet_cache = Cache()#(CACHE_TYPE='filesystem', CACHE_DIR='cache')
logger = logging.getLogger("bot.contracts")
if not logger.handlers:
	file_handler = logging.FileHandler("logs/contracts.log")
	file_handler.setFormatter(FILE_LOGGING_FORMATTER)
	console_handler = logging.StreamHandler()
	console_handler.setFormatter(CONSOLE_LOGGING_FORMATTER)
	logger.addHandler(file_handler)
	logger.addHandler(console_handler)

	logger.setLevel(logging.INFO)

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
		username = row[1].strip().lower()
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

			contracts[row_name] = Contract(
				name=row_content.replace("\n", ", "),
				passed=passed_contract
			)

		user_passed_contracts = True if status == "P" else False
		if user_passed_contracts:
			users_passed += 1

		season.users[username] = User(
			name=username,
			status="PASSED" if status == "P" else "FAILED" if status == "F" else status,
			contracts=contracts
		)
	
	season.stats = SeasonStats(
		users=len(season.users),
		users_passed=users_passed,
		contracts=total_contracts,
		contracts_passed=total_contracts_passed,
		contract_types=per_contract_stats
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
		user.rep = row[2]
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
		base_contract.progress = row[29].replace("\n", "") if len(row) > 29 and row[29] != "" else "?/?"
		base_contract.rating = row[26]
		base_contract.review_url = _get_first_url(row[31] if len(row) > 31 else "")
		base_contract.medium = row[9]
		if "Challenge Contract" in user.contracts:
			challenge_contract: Contract = user.contracts["Challenge Contract"]
			challenge_contract.contractor = contractor
			challenge_contract.status = row[1]
			challenge_contract.progress = row[30] if len(row) > 30 and row[30] != "" else "?/?"
			challenge_contract.rating = row[28]
			challenge_contract.review_url = _get_first_url(row[32] if len(row) > 32 else "")
			challenge_contract.medium = row[13]

def _add_specials_data(season: Season, sheet_data):
	# Veteran Special Sheet
	rows: list[list[str]] = sheet_data["valueRanges"][2]["values"]

	for row in rows:
		username = row[2].strip().lower()
		if username not in season.users:
			continue
		user = season.users[username]
		veteran_special = user.contracts["Veteran Special"]
		veteran_special.status = row[5]
		veteran_special.progress = row[6] if len(row) > 6 and row[6] != "" else "?/?"
		veteran_special.rating = row[7]
		veteran_special.review_url = _get_first_url(row[8]) if len(row) > 8 else ""
		veteran_special.contractor = row[4].strip().lower()
		veteran_special.medium = re.sub(CONTRACT_NAME_MEDIUM_REGEX, r"\2", row[3])
	
	# VN Special Sheet
	rows: list[list[str]] = sheet_data["valueRanges"][3]["values"]
	for row in rows:
		username = row[2].strip().lower()
		if username not in season.users:
			continue
		user = season.users[username]
		vn_special = user.contracts["VN Special"]
		vn_special.status = row[0]
		vn_special.progress = "Completed" if row[0] == "PASSED" else "Not Completed"
		vn_special.rating = row[5]
		vn_special.review_url = _get_first_url(row[6]) if len(row) > 6 else ""
		vn_special.contractor = row[4].strip().lower()
		vn_special.medium = "VN"
	
	# Movie Special Sheet
	rows: list[list[str]] = sheet_data["valueRanges"][4]["values"]
	for row in rows:
		username = row[2].strip().lower()
		if username not in season.users:
			continue
		user = season.users[username]
		movie_special = user.contracts["Movie Special"]
		movie_special.status = row[0]
		movie_special.progress = "Completed" if row[0] == "PASSED" else "Not Completed"
		movie_special.rating = row[5]
		movie_special.review_url = _get_first_url(row[6]) if len(row) > 6 else ""
		movie_special.contractor = row[4].strip().lower()
		movie_special.medium= "Movie"
	
	# Indie Special Sheet
	rows: list[list[str]] = sheet_data["valueRanges"][5]["values"]
	for row in rows:
		username = row[2].strip().lower()
		if username not in season.users:
			continue
		user = season.users[username]
		indie_special = user.contracts["Indie Special"]
		indie_special.status = row[0]
		indie_special.progress = row[5]
		indie_special.rating = row[6]
		indie_special.review_url = _get_first_url(row[7]) if len(row) > 7 else ""
		indie_special.contractor = row[4].strip().lower()
		indie_special.medium = "Game"
	
	# Extreme Special Sheet
	rows: list[list[str]] = sheet_data["valueRanges"][6]["values"]
	for row in rows:
		username = row[2].strip().lower()
		if username not in season.users:
			continue
		user = season.users[username]
		extreme_special = user.contracts["Extreme Special"]
		extreme_special.status = row[0]
		extreme_special.progress = "Completed" if row[0] == "PASSED" else "Not Completed"
		extreme_special.rating = row[5]
		extreme_special.review_url = _get_first_url(row[6]) if len(row) > 6 else ""
		extreme_special.contractor = row[4].strip().lower()
		extreme_special.medium = "Game"
	
	# Buddying Sheet
	rows: list[list[str]] = sheet_data["valueRanges"][7]["values"]
	for row in rows:
		username = row[2].strip().lower()
		if username not in season.users:
			continue
		user = season.users[username]
		if "Base Buddy" in user.contracts:
			buddy_base = user.contracts["Base Buddy"]
			buddy_base.status = row[0]
			buddy_base.contractor = row[4].strip().lower()
			buddy_base.progress = row[8] if row[8] != "" else "?/?"
			buddy_base.rating = row[10]
			buddy_base.review_url = _get_first_url(row[12]) if len(row) > 12 else ""
			buddy_base.medium = "Anime / Manga"
		if "Challenge Buddy" in user.contracts:
			buddy_challenge = user.contracts["Challenge Buddy"]
			buddy_challenge.status = row[1]
			buddy_challenge.contractor = row[6].strip().lower()
			buddy_challenge.progress = row[9] if row[9] != "" else "?/?"
			buddy_challenge.rating = row[11]
			buddy_challenge.review_url = _get_first_url(row[13]) if len(row) > 13 else ""
			buddy_challenge.medium = "Anime / Manga"

def _convert_sheet_to_season(sheet_data) -> Season:
	season = _get_season_dashboard_data(sheet_data)

	_add_basechallenge_data(season, sheet_data)
	_add_specials_data(season, sheet_data)

	return season

@season_sheet_cache.memoize(timeout=2.5 * 60)#SHEET_DATA_CACHE_DURATION * 60 * 60)
def get_season_data() -> tuple[Season, float]:
	with httpx.Client() as client:
		response = client.get(GET_SHEET_DATA_URL, params={
			"majorDimension": "ROWS",
			"valueRenderOption": "FORMATTED_VALUE",
			"ranges": [
				"Dashboard!A2:U394",
				"Base!A2:AG394",
				"Veteran Special!A2:I167",
				"VN Special!A2:G126",
				"Movie Special!A2:H243",
				"Indie Special!A2:H136",
				"Extreme Special!A2:G95",
				"Buddying!A2:N68"
			],
			"key": os.getenv("GOOGLE_API_KEY")
		})
		response.raise_for_status()
		#logger.info(f"Season data has been cached for {SHEET_DATA_CACHE_DURATION} hour(s)!")
		return _convert_sheet_to_season(response.json()), datetime.datetime.now(datetime.UTC).timestamp()