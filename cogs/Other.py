import discord
from globals import *
from discord.ext import commands
from discord.commands import slash_command

class Other(commands.Cog):
	def __init__(self, bot: commands.Bot):
		self.bot = bot

	@commands.Cog.listener()
	async def on_command_error(self, ctx: commands.Context, error):
		if isinstance(error, commands.CommandNotFound):
			return
		elif isinstance(error, commands.NotOwner):
			return
		elif isinstance(error, commands.MissingPermissions):
			return
		elif isinstance(error, commands.CommandOnCooldown):
			await ctx.reply(content=f"This command is currently on cooldown! Please retry in **{error.retry_after:.2f}** seconds!", delete_after=3)
		else:
			embed = discord.Embed(description=error,color=discord.Color.red())
			embed.title = f"An unexpected error occured when trying to run ``{config['prefix']}{ctx.command.qualified_name}``"
			embed.set_footer(text=f"Requested by @{ctx.author.name}", icon_url=ctx.author.display_avatar.url)
			await ctx.reply(embed=embed,delete_after=5)

	@commands.Cog.listener()
	async def on_application_command_error(self, ctx: discord.ApplicationContext, error: discord.DiscordException):
		if isinstance(error, commands.CommandOnCooldown):
			await ctx.respond(content=f"This command is currently on cooldown! Please retry in **{error.retry_after:.2f}** seconds!", ephemeral=True)
		else:
			embed = discord.Embed(description=error,color=discord.Color.red())
			embed.title = f"An unexpected error occured when trying to run /{ctx.command.qualified_name}"
			embed.set_footer(text=f"Requested by @{ctx.author.name}", icon_url=ctx.author.display_avatar.url)
			await ctx.respond(embed=embed, ephemeral=True)

	@commands.command(name="ping")
	async def ping(self, ctx: commands.Context):
		ping = round(self.bot.latency * 1000)
		await ctx.reply(f"{ping}ms :ping_pong:")

def setup(bot:commands.Bot):
	bot.add_cog(Other(bot))