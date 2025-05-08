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

	@commands.command(help="Fetch information on the bot.")
	async def info(self, ctx: commands.Context):
		ping_ms = round(self.bot.latency * 1000)

		owner_names = []
		for owner in config.BOT_CONFIG.owner_ids:
			owner_names.append(f"**<@{owner}>**")

		embed = discord.Embed(title=self.bot.user.name, color=config.BASE_EMBED_COLOR, description="")
		embed.set_thumbnail(url=self.bot.user.avatar.url)
		embed.description += f"{self.bot.user.name} is open source! The source code is available [here]({config.BOT_CONFIG.repository_link}) and licensed under [GNU GPLv3](https://raw.githubusercontent.com/TrhRichard/Natsumin/refs/heads/main/LICENSE)."
		embed.description += f"\n> **Ping**: {ping_ms}ms"
		embed.description += f"\n> **Prefix**: {config.BOT_CONFIG.prefix}"
		embed.description += f"\n> **Maintainers**: {', '.join(owner_names)}"
		await ctx.reply(embed=embed)

	@commands.command(name="info", description="Fetch information on the bot.")
	async def slash_info(self, ctx: discord.ApplicationContext):
		ping_ms = round(self.bot.latency * 1000)

		owner_names = []
		for owner in config.BOT_CONFIG.owner_ids:
			owner_names.append(f"**<@{owner}>**")

		embed = discord.Embed(title=self.bot.user.name, color=config.BASE_EMBED_COLOR, description="")
		embed.set_thumbnail(url=self.bot.user.avatar.url)
		embed.description += f"{self.bot.user.name} is open source! The source code is available [here]({config.BOT_CONFIG.repository_link}) and licensed under [GNU GPLv3](https://raw.githubusercontent.com/TrhRichard/Natsumin/refs/heads/main/LICENSE)."
		embed.description += f"\n> **Ping**: {ping_ms}ms"
		embed.description += f"\n> **Prefix**: {config.BOT_CONFIG.prefix}"
		embed.description += f"\n> **Maintainers**: {', '.join(owner_names)}"
		await ctx.respond(embed=embed)

	@commands.command(help="Fetch information on the bot.", aliases=["latency"])
	async def ping(self, ctx: commands.Context):
		embed = discord.Embed(color=config.BASE_EMBED_COLOR)
		embed.description = f":ping_pong: Pong! ({round(self.bot.latency * 1000)}ms)"
		await ctx.reply(embed=embed)

	@commands.slash_command(name="ping", description="Ping the bot.")
	async def slash_ping(self, ctx: discord.ApplicationContext):
		embed = discord.Embed(color=config.BASE_EMBED_COLOR)
		embed.description = f":ping_pong: Pong! ({round(self.bot.latency * 1000)}ms)"
		await ctx.respond(embed=embed)


def setup(bot: commands.Bot):
	bot.add_cog(Other(bot))
