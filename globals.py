import json
import discord
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

class ContractsStats(TypedDict):
	users: int
	users_passed: int
	contracts: int
	contracts_passed: int
	contract_types: dict[str, list[int]]

class ContractsDatabase(TypedDict):
	users: dict[str, ContractsUser]
	stats: ContractsStats

NATSUMIN_EMBED_COLOR = discord.Color.from_rgb(67, 79, 93)