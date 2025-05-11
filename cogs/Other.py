from discord.ext import commands
import logging
import discord
import config


class Other(commands.Cog):
	def __init__(self, bot: commands.Bot):
		self.bot = bot
		self.logger = logging.getLogger("bot.other")

		if not self.logger.handlers:
			file_handler = logging.FileHandler("logs/other.log", encoding="utf-8")
			file_handler.setFormatter(config.FILE_LOGGING_FORMATTER)
			console_handler = logging.StreamHandler()
			console_handler.setFormatter(config.CONSOLE_LOGGING_FORMATTER)
			self.logger.addHandler(file_handler)
			self.logger.addHandler(console_handler)
			self.logger.setLevel(logging.INFO)

	@commands.command(help="Fetch information on the bot")
	async def botinfo(self, ctx: commands.Context):
		ping_ms = round(self.bot.latency * 1000)

		owner_names = []
		for owner in config.BOT_CONFIG.owner_ids:
			owner_names.append(f"**<@{owner}>**")
		contributor_names = []
		for contributor in config.BOT_CONFIG.contributor_ids:
			contributor_names.append(f"**<@{contributor}>**")

		embed = discord.Embed(title=self.bot.user.name, color=config.BASE_EMBED_COLOR, description="")
		embed.set_thumbnail(url=self.bot.user.avatar.url)
		embed.description += f"{self.bot.user.name} is a bot made for Anicord Event Server to assist with contracts related stuff. If you would like to contribute to it's development you can do it [here]({config.BOT_CONFIG.repository_link})."
		embed.description += f"\n> **Ping**: {ping_ms}ms"
		embed.description += f"\n> **Prefix**: {config.BOT_CONFIG.prefix}"
		embed.description += f"\n> **Maintainers**: {', '.join(owner_names)}"
		embed.description += f"\n> **Contributors**: {','.join(contributor_names)}"
		await ctx.reply(embed=embed)

	@commands.slash_command(name="botinfo", description="Fetch information on the bot")
	async def slash_botinfo(self, ctx: discord.ApplicationContext):
		ping_ms = round(self.bot.latency * 1000)

		owner_names = []
		for owner in config.BOT_CONFIG.owner_ids:
			owner_names.append(f"**<@{owner}>**")
		contributor_names = []
		for contributor in config.BOT_CONFIG.contributor_ids:
			contributor_names.append(f"**<@{contributor}>**")

		embed = discord.Embed(title=self.bot.user.name, color=config.BASE_EMBED_COLOR, description="")
		embed.set_thumbnail(url=self.bot.user.avatar.url)
		embed.description += f"{self.bot.user.name} is a bot made for Anicord Event Server to assist with contracts related stuff. If you would like to contribute to it's development you can do it [here]({config.BOT_CONFIG.repository_link})."
		embed.description += f"\n> **Ping**: {ping_ms}ms"
		embed.description += f"\n> **Prefix**: {config.BOT_CONFIG.prefix}"
		embed.description += f"\n> **Maintainers**: {', '.join(owner_names)}"
		embed.description += f"\n> **Contributors**: {','.join(contributor_names)}"
		await ctx.respond(embed=embed)

	@commands.command(help="Check the bot's latency", aliases=["latency"])
	async def ping(self, ctx: commands.Context):
		embed = discord.Embed(color=config.BASE_EMBED_COLOR)
		embed.description = f":ping_pong: Pong! ({round(self.bot.latency * 1000)}ms)"
		await ctx.reply(embed=embed)

	@commands.slash_command(name="ping", description="Check the bot's latency")
	async def slash_ping(self, ctx: discord.ApplicationContext):
		embed = discord.Embed(color=config.BASE_EMBED_COLOR)
		embed.description = f":ping_pong: Pong! ({round(self.bot.latency * 1000)}ms)"
		await ctx.respond(embed=embed)

	@commands.command(help="Helpful information on bot related stuff")
	async def usage(self, ctx: commands.Context):
		embed = discord.Embed(color=config.BASE_EMBED_COLOR)
		embed.description = """
- Meanings of each emoji next to a username:
  - ❌: Failed
  - ✅: Passed
  - ⌛☑️: Late Pass
  - ⛔: Incomplete (Partial Fail)
- For commands that take a username as an argument you can do the following:
  - `[contractee]`: Your contractee in the season
  - `[contractor]`: Your contractor in the season
    - For each of the options above you can add a username before to check for that user, for example: ``frazzle_dazzle[contractee]``
"""
		await ctx.reply(embed=embed)


def setup(bot: commands.Bot):
	bot.add_cog(Other(bot))
