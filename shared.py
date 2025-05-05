import json
from typing import Optional, TypedDict
import discord
from discord.ext import commands


def get_member_from_username(bot: commands.Bot, username: str) -> Optional[discord.Member]:
	for member in bot.get_all_members():
		if member.name.lower() == username.lower():
			return member
	return None

class NiceMessageCategory(TypedDict):
	same_user: list[str]
	different_user: list[str]
	is_contractor: list[str]

class NiceMessages(TypedDict):
	finished: NiceMessageCategory
	halfway: NiceMessageCategory
	started: NiceMessageCategory
	not_started: NiceMessageCategory

with open("assets/nice_messages.json") as f:
	nice_messages: NiceMessages = json.load(f)