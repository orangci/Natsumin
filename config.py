import logging
import yaml
import dataclasses
import datetime


@dataclasses.dataclass
class Config:
    guild_ids: list[int]
    prefix: str
    owner_ids: list[int]


with open("config.yaml", "r") as file:
    BOT_CONFIG = Config(**yaml.full_load(file))

BASE_EMBED_COLOR = 0xF5C2E7
FILE_LOGGING_FORMATTER = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s", "%Y-%m-%d %H:%M:%S"
)
CONSOLE_LOGGING_FORMATTER = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s", "%H:%M:%S"
)

# set the unix time of the season's deadline here
DEADLINE_TIMESTAMP_INT = 1746943200
DEADLINE_TIMESTAMP = datetime.datetime.fromtimestamp(
    DEADLINE_TIMESTAMP_INT, datetime.UTC
)
