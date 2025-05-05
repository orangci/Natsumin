import logging
import discord
from config import BASE_EMBED_COLOR, BOT_CONFIG, CONSOLE_LOGGING_FORMATTER, FILE_LOGGING_FORMATTER
from discord.ext import commands

class Other(commands.Cog):
	def __init__(self, bot: commands.Bot):
		self.bot = bot
		self.logger = logging.getLogger("bot.other")

		if not self.logger.handlers:
			file_handler = logging.FileHandler("logs/other.log", encoding="utf-8")
			file_handler.setFormatter(FILE_LOGGING_FORMATTER)
			console_handler = logging.StreamHandler()
			console_handler.setFormatter(CONSOLE_LOGGING_FORMATTER)
			self.logger.addHandler(file_handler)
			self.logger.addHandler(console_handler)

			self.logger.setLevel(logging.INFO)

	@commands.command(help="Get information regarding the bot")
	async def info(self, ctx: commands.Context):
		ping_ms = round(self.bot.latency * 1000)
		user: discord.Member | discord.User = ctx.author

		embed = discord.Embed(title="Bot Info", color=BASE_EMBED_COLOR)
		embed.set_thumbnail(url=self.bot.user.avatar.url)
		embed.add_field(name="Ping", value=f"{ping_ms}ms")
		embed.add_field(name="Prefix", value=f"{BOT_CONFIG.prefix}")
		embed.add_field(name="Author", value=f"<@{BOT_CONFIG.owner_id}>")
		embed.set_footer(text=f"Requested by {user.display_name}", icon_url=user.avatar.url)
		await ctx.reply(embed=embed)
		

def setup(bot: commands.Bot):
	bot.add_cog(Other(bot))