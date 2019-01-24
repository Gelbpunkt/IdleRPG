import sys, os
from platform import python_version
import traceback
import asyncio
import uvloop
import aiohttp
import discord
from discord.ext import commands
import asyncpg
import aioredis

import config
from utils.checks import is_hypesquad
from utils.loops import queue_manager

if sys.platform == "linux" and sys.version_info >= (
    3,
    5,
):  # uvloop requires linux and min 3.5 Python
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


def get_prefix(bot, message):
    if not message.guild or bot.config.is_beta:
        return (
            bot.config.global_prefix
        )  # Use global prefix in DMs and if the bot is beta
    try:
        return commands.when_mentioned_or(bot.all_prefixes[message.guild.id])(
            bot, message
        )
    except:
        return commands.when_mentioned_or(bot.config.global_prefix)(bot, message)
    return bot.config.global_prefix


bot = commands.AutoShardedBot(
    command_prefix=get_prefix,
    case_insensitive=True,
    description="The one and only IdleRPG bot for discord",
)
bot.version = "3.3 stable"
bot.remove_command("help")
bot.config = config
bot.BASE_URL = config.base_url

bot.linecount = 0

with open("idlerpg.py", encoding="utf-8") as f:
    bot.linecount += len(f.readlines())
for afile in os.listdir("cogs"):
    if os.path.isdir(afile) or not afile.endswith(".py"):
        continue
    with open(f"cogs/{afile}", "r", encoding="utf-8") as f:
        bot.linecount += len(f.readlines())


async def create_pool():
    credentials = bot.config.database
    credentials = {
        "database": credentials[0],
        "user": credentials[1],
        "password": credentials[2],
        "host": credentials[3],
    }
    pool = await asyncpg.create_pool(**credentials, max_size=100)
    return pool


async def start_bot():
    bot.session = aiohttp.ClientSession(loop=bot.loop)
    bot.redis = await aioredis.create_pool(
        "redis://localhost", minsize=5, maxsize=10, loop=bot.loop
    )
    pool = await create_pool()
    bot.pool = pool
    bot.all_prefixes = {}
    async with bot.pool.acquire() as conn:
        prefixes = await conn.fetch("SELECT id, prefix FROM server;")
        for row in prefixes:
            bot.all_prefixes[row[0]] = row[1]
    await bot.start(bot.config.token)


map = commands.CooldownMapping.from_cooldown(1, 3, commands.BucketType.user)


@bot.check_once
async def global_cooldown(ctx: commands.Context):
    bucket = map.get_bucket(ctx.message)
    retry_after = bucket.update_rate_limit()

    if retry_after:
        raise commands.CommandOnCooldown(bucket, retry_after)
    else:
        return True


bot.bans = [
    314_210_539_498_897_418,
    326_069_549_042_630_657,
    416_072_373_750_595_584,
    283_291_722_749_050_883,
    298_267_992_221_810_689,
    121_469_467_782_807_552,
    155_696_684_716_785_664,
    206_439_870_288_101_386,
    448_987_127_712_317_465,
    138_058_071_619_534_848,
    440_648_947_850_149_888,
]


@bot.event
async def on_message(message):
    if message.author.bot or message.author.id in bot.bans:
        return
    await bot.process_commands(message)


@bot.event
async def on_ready():
    print(
        f"Logged in as {bot.user.name} (ID: {bot.user.id}) | Connected to {len(bot.guilds)} servers | Connected to {len(bot.users)} users"
    )
    print("--------")
    print(
        f"Current Discord.py Version: {discord.__version__} | Current Python Version: {python_version()}"
    )
    print("--------")
    print(f"Use this link to invite {bot.user.name}:")
    print(
        f"https://discordapp.com/oauth2/authorize?client_id={bot.user.id}&scope=bot&permissions=8"
    )
    print("--------")
    print("Support Discord Server: https://discord.gg/MSBatf6")
    print("--------")
    print(f"You are running IdleRPG Bot {bot.version}")
    owner = (await bot.application_info()).owner
    bot.owner_id = owner.id
    print(f"Created by {owner}")
    bot.loop.create_task(queue_manager(bot, bot.queue))


if __name__ == "__main__":
    bot.queue = asyncio.Queue(loop=bot.loop)  # global queue for ordered tasks
    for extension in bot.config.initial_extensions:
        try:
            bot.load_extension(extension)
        except Exception as e:
            print(f"Failed to load extension {extension}.", file=sys.stderr)
            traceback.print_exc()
    if bot.config.is_beta:  # TODO: find a better place for this (maybe a beta cog)
        bot.add_check(is_hypesquad)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_bot())
