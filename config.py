import logging
import yaml
import dataclasses
import discord

@dataclasses.dataclass
class Config:
	guild_ids: list[int]
	prefix: str
	owner_id: int

with open("config.yaml", "r") as file:
	BOT_CONFIG = Config(**yaml.full_load(file))

BASE_EMBED_COLOR = discord.Color.from_rgb(67, 79, 93)
FILE_LOGGING_FORMATTER = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s", "%Y-%m-%d %H:%M:%S")
CONSOLE_LOGGING_FORMATTER = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s", "%H:%M:%S")