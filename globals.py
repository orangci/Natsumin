import json
from typing import TypedDict

class BotConfig(TypedDict):
	debug_servers: list[int]
	prefix: str
	owner_id: int

with open("config.json") as f:
	config: BotConfig = json.load(f)

class ContractData(TypedDict):
	name: str
	passed: bool

class ContractsUser(TypedDict):
	status: str
	contracts: dict[str, ContractData]