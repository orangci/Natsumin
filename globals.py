import json
import discord
from typing import TypedDict

class BotConfig(TypedDict):
	debug_servers: list[int]
	prefix: str
	owner_id: int

with open("config.json") as f:
	config: BotConfig = json.load(f)

NATSUMIN_EMBED_COLOR = discord.Color.from_rgb(67, 79, 93)