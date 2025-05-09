from typing import Mapping, Optional
from config import BOT_CONFIG, BASE_EMBED_COLOR
from contracts import cache_reset_loop
from discord.ext import commands
from dotenv import load_dotenv
import asyncio
import discord
import os

load_dotenv()
bot = commands.Bot(
	command_prefix=BOT_CONFIG.prefix,
	status=discord.Status.online,
	activity=discord.CustomActivity(name="?/? users passed | %help"),
	intents=discord.Intents.all(),
	case_insensitive=True,
	allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=True, replied_user=False),
)


@bot.event
async def on_ready():
	os.system("cls" if os.name == "nt" else "clear")
	print(f"Logged in as {bot.user.name}#{bot.user.discriminator}!")
	asyncio.create_task(cache_reset_loop())


def recursive_load_cogs(path: str):
	for file in os.listdir(path):
		if file.endswith(".py") and not file.startswith("_"):
			cog_name = f"{path.replace('/', '.')}.{file[0:-3]}"
			bot.load_extension(cog_name)
			continue
		if os.path.isdir(f"{path}/{file}"):
			recursive_load_cogs(f"{path}/{file}")


class Help(commands.HelpCommand):
	def get_command_signature(self, command: commands.Command):
		return "%s%s %s %s" % (self.context.clean_prefix, command.qualified_name, command.signature, ("- " + command.help) if command.help else "")

	async def send_bot_help(self, mapping: Mapping[Optional[commands.Cog], list[commands.Command]]):
		embed = discord.Embed(color=BASE_EMBED_COLOR)

		for cog, cog_commands in mapping.items():
			filtered: list[commands.Command] = await self.filter_commands(cog_commands, sort=True)
			command_signatures = [self.get_command_signature(c) for c in filtered]

			if command_signatures:
				cog_name = getattr(cog, "qualified_name", "No Category")
				embed.add_field(name=cog_name, value="\n".join([f"> {s}" for s in command_signatures]), inline=False)

		channel = self.get_destination()
		await channel.send(embed=embed)

	async def send_command_help(self, command: commands.Command):
		embed = discord.Embed(color=BASE_EMBED_COLOR)

		embed.description = f"{self.context.clean_prefix}{command.qualified_name} {command.signature}"
		if len(command.aliases) > 0:
			embed.description += f"\n> **Aliases**: {', '.join(command.aliases)}"

		if command.help:
			embed.description += f"\n\n{command.help}"

		channel = self.get_destination()
		await channel.send(embed=embed)

	async def send_cog_help(self, cog: commands.Cog):
		embed = discord.Embed(color=BASE_EMBED_COLOR)

		filtered: list[commands.Command] = await self.filter_commands(cog.get_commands(), sort=True)
		command_signatures = [self.get_command_signature(c) for c in filtered]

		if command_signatures:
			cog_name = getattr(cog, "qualified_name", "No Category")
			embed.add_field(name=cog_name, value="\n".join([f"> {s}" for s in command_signatures]), inline=False)

		channel = self.get_destination()
		await channel.send(embed=embed)


bot.help_command = Help()


recursive_load_cogs("cogs")
bot.run(os.getenv("DISCORD_TOKEN"))
