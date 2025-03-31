import discord
import os
from globals import *
from discord.ext import commands
from dotenv import load_dotenv

def clear():
	if os.name == "nt":
		os.system("cls")
	else:
		os.system("clear")

load_dotenv()
bot=commands.Bot(
	command_prefix = commands.when_mentioned_or(config["prefix"]),
	status = discord.Status.dnd,
	intents = discord.Intents.all(),
	owner_id = config["owner_id"]
)
bot.remove_command('help')

@bot.event
async def on_ready():
	clear()
	print(f"{bot.user.name}#{bot.user.discriminator} is now online.\n")

clear()

def recursive_load(path: str):
	for file in os.listdir(path):
		if file.endswith(".py") and not file.endswith(".disabled.py"):
			bot.load_extension(f"{path}.{file[0:-3]}")
			print(f"Cog \"{file[0:-3]}\" is now loaded.")
			continue
		if not file.startswith("_") and os.path.isdir(f"{path}/{file}"):
			recursive_load(f"{path}/{file}")

recursive_load("cogs")
bot.run(os.getenv("DISCORD_TOKEN"))