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

		embed = discord.Embed(
			title=self.bot.user.name,
			color=config.BASE_EMBED_COLOR,
			description="",
		)
		embed.set_thumbnail(url=self.bot.user.avatar.url)
		embed.description += f"> **Ping**: {ping_ms}ms"
		embed.description += f"\n> **Prefix**: {config.BOT_CONFIG.prefix}"
		embed.description += f"\n> **Authors**: {', '.join(owner_names)}"

		embed.set_footer(
			text=f"Requested by {ctx.author.display_name}",
			icon_url=ctx.author.avatar.url,
		)
		await ctx.reply(embed=embed)

	@commands.command(help="Fetch information on the bot.", aliases=["latency"])
	async def ping(self, ctx: commands.Context):
		ping_ms = round(self.bot.latency * 1000)

		await ctx.reply(content=f"Pong! ({ping_ms}ms)")


def setup(bot: commands.Bot):
	bot.add_cog(Other(bot))
