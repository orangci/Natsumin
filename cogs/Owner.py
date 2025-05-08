from config import CONSOLE_LOGGING_FORMATTER, FILE_LOGGING_FORMATTER, BASE_EMBED_COLOR
from shared import get_member_from_username
from contracts import get_season_data
from discord.ext import commands
from dataclasses import asdict
from typing import Optional
import datetime
import logging
import discord
import json
import io


class DeleteMessageView(discord.ui.View):
	def __init__(self, timeout: Optional[float] = 300, user_id: Optional[int] = None):
		super().__init__(timeout=timeout)
		self.user_id = user_id

	@discord.ui.button(label="Delete", style=discord.ButtonStyle.red)
	async def delete(self, button: discord.ui.Button, interaction: discord.Interaction):
		if self.user_id and interaction.user.id != self.user_id:
			await interaction.response.send_message("You can't delete this message!", ephemeral=True)
			return
		await interaction.response.edit_message(view=None)
		await interaction.delete_original_response()


class Owner(commands.Cog):
	def __init__(self, bot: commands.Bot):
		self.bot = bot
		self.logger = logging.getLogger("bot.owner")

		if not self.logger.handlers:
			file_handler = logging.FileHandler("logs/owner.log", encoding="utf-8")
			file_handler.setFormatter(FILE_LOGGING_FORMATTER)
			console_handler = logging.StreamHandler()
			console_handler.setFormatter(CONSOLE_LOGGING_FORMATTER)
			self.logger.addHandler(file_handler)
			self.logger.addHandler(console_handler)

			self.logger.setLevel(logging.INFO)

	@commands.command(hidden=True)
	@commands.is_owner()
	async def get_season_file(self, ctx: commands.Context):
		season, _ = await get_season_data()
		database_file = discord.File(io.BytesIO(json.dumps(asdict(season), indent=4).encode("utf-8")))
		database_file.filename = "winter_2025.json"
		expire_datetime = datetime.datetime.now(datetime.UTC) + datetime.timedelta(seconds=30)
		await ctx.reply(
			content=f"Message will expire <t:{int(expire_datetime.timestamp())}:R>",
			file=database_file,
			view=DeleteMessageView(30, ctx.author.id),
			delete_after=30,
		)

	@commands.command(hidden=True, aliases=["purge_cache"])
	@commands.is_owner()
	async def clear_cache(self, ctx: commands.Context):
		get_season_data.cache_clear()
		self.logger.info(f"Cache has been purged by @{ctx.author.name} ({ctx.author.id})")
		await ctx.reply("Cache purged.\nNext command will request updated data.", delete_after=3)

	@commands.command(hidden=True)
	@commands.is_owner()
	async def get_users(self, ctx: commands.Context, rep: str = "*", passed_status: str = "*"):
		season, _ = await get_season_data()
		rep = rep.replace(" ", "-").lower()
		passed_status = passed_status.lower()
		if passed_status not in ["all", "*", "passed", "failed", "pending"]:
			await ctx.reply("Invalid status! Use `all`, `*`, `passed`, `failed` or `pending`")
			return
		if rep not in ["all", "*"] and rep not in [user.rep.replace(" ", "-").lower() for user in season.users.values()]:
			await ctx.reply("Invalid rep! Use `all`, `*` or a valid rep")
			return

		pending_ids = []
		pending_usernames = []
		if passed_status == "pending":
			passed_status = ""
		for username, user in season.users.items():
			if passed_status not in ["all", "*"] and user.status.lower() != passed_status:
				continue
			if rep not in ["all", "*"] and user.rep.replace(" ", "-").lower() != rep:
				continue

			member = get_member_from_username(self.bot, username)
			pending_usernames.append(username)
			if member:
				pending_ids.append(member.id)

		if len(pending_usernames) == 0:
			await ctx.reply("No users found with those filters!")
			return

		usernames_file = discord.File(io.BytesIO("\n".join(pending_usernames).encode("utf-8")))
		usernames_file.filename = "usernames.txt"

		if len(pending_ids) != 0:
			mentions_file = discord.File(io.BytesIO("\n".join([f"<@{userid}>" for userid in pending_ids]).encode("utf-8")))
			mentions_file.filename = "mentions.txt"

		await ctx.reply(
			content=f"Found {len(pending_usernames)} users with the filters:\n- Rep: `{rep}`\n- Status: `{passed_status}`",
			files=[usernames_file, mentions_file] if len(pending_ids) != 0 else [usernames_file],
		)

	@commands.command(hidden=True)
	@commands.is_owner()
	async def delete_message(self, ctx: commands.Context, message_id: int, channel_id: int = None):
		message = self.bot.get_message(message_id)
		if not message:
			if channel_id is None:
				await ctx.reply("Channel ID argument required for uncached message!", delete_after=3)
				return
			message_channel = self.bot.get_channel(channel_id)
			if not message_channel:
				message_channel = await self.bot.fetch_channel(channel_id)
			message = await message_channel.fetch_message(message_id)

		if message is None:
			await ctx.reply("Could not find the message you requested!", delete_after=3)
			return

		if message.author.id != self.bot.user.id:
			await ctx.reply("This command can only be used to delete the bot's messages!", delete_after=3)
			return

		await message.delete()
		await ctx.reply("Message deleted!", delete_after=3)

	@commands.command(hidden=True, aliases=["r"])
	@commands.is_owner()
	async def reload_exts(self, ctx: commands.Context):
		failed_cogs = []
		for cog in list(self.bot.extensions.keys()):
			try:
				self.bot.reload_extension(cog)
			except Exception as e:
				failed_cogs.append(f"{cog}: {e}")

		if failed_cogs:
			error_message = "❌ Reloaded all except the following cogs:\n" + "\n> ".join(failed_cogs)
			embed = discord.Embed(color=discord.Color.red(), description=error_message)
			await ctx.reply(embed=embed, mention_author=False)
		else:
			embed = discord.Embed(color=BASE_EMBED_COLOR, description="✅ Successfully reloaded all cogs.")
			await ctx.reply(embed=embed, mention_author=False)

	@commands.command(hidden=True, aliases=["rsc"])
	@commands.is_owner()
	async def reload_slash_command(self, ctx: commands.Context):
		await self.bot.sync_commands()
		embed = discord.Embed(color=BASE_EMBED_COLOR)
		embed.description = "✅ Successfully synced bot application commands."
		await ctx.reply(embed=embed, mention_author=False)


def setup(bot: commands.Bot):
	bot.add_cog(Owner(bot))
