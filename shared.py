import discord
from discord.ext import commands


def get_member_from_username(bot: commands.Bot, username: str) -> discord.Member | None:
	for member in bot.get_all_members():
		if member.name.lower() == username.lower():
			return member
	return None
