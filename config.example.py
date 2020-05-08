"""Ignore this"""
from datetime import timedelta

from discord.ext import commands

"""End ignore"""

"""The token it will use for auth with Discord."""
token = "my cool bot token"

"""The Postgres database credentials."""
database = {
    "database": "database_name",
    "user": "database_user",
    "password": "database_password",
    "host": "localhost",
}

"""A token for the Discord Bot List (DBL)."""
dbltoken = "dbltoken"

"""A token for the Bots For Discord Website (BFD)."""
bfdtoken = "bfdtoken"

"""All cogs to load on startup."""
initial_extensions = [
    "cogs.locale",
    "cogs.owner",
    "cogs.game_master",
    "cogs.gambling",
    "cogs.adventure",
    "cogs.ranks",
    "cogs.trading",
    "cogs.miscellaneous",
    "cogs.server",
    "cogs.profile",
    "cogs.battles",
    "cogs.help",
    "cogs.vote",
    "cogs.crates",
    "cogs.patreon",
    "cogs.store",
    "cogs.marriage",
    "cogs.guild",
    "cogs.tournament",
    "cogs.classes",
    "cogs.images",
    "cogs.global_events",
    "cogs.raid",
    "cogs.music",
    "cogs.custom",
    "cogs.gods",
    "cogs.transaction",
    "cogs.races",
    "cogs.hungergames",
    "cogs.maths",
    "cogs.shard_communication",
    "cogs.alliance",
    "cogs.trivia",
    "cogs.chess",
    "cogs.werewolf",
    "cogs.error_handler",
]

"""The prefix to use if none is set custom or we are in DMs."""
global_prefix = "$"

"""Extra shards to launch on bot startup"""
additional_shards = 4

"""How many shard a process will handle (at max)"""
shard_per_cluster = 4

"""The channel ID to send join logs to."""
join_channel = 1234567890

"""Defines whether it is a beta version or not. This would disable some parts, e.g. no longer post the stats to DBL and BFD."""
is_beta = True

"""A list of Game Masters by ID."""
game_masters = [1234567890]

"""A list of banned users."""
bans = [1234567890]

"""The support server ID."""
support_server_id = 1234567890

"""The ID to allow mass tournaments from."""
official_tournament_channel_id = 1234567890

"""A channel ID to send GM logs to."""
gm_log_channel = 1234567890

"""A channel ID to send public logs to."""
bot_event_channel = 1234567890

"""City config (must be in db)"""
cities = {
    "Vopnafjor": ("thief", "raid", "trade", "adventure"),
    "Medriguen": ("raid", "trade", "adventure"),
    "Sulitere": ("raid", "trade", "thief"),
    "Mopra": ("raid", "trade"),
    "Setrond": ("thief", "trade"),
    "Armeles": ("adventure", "trade"),
    "Weyeowen": ("thief",),
    "Oltash": ("trade",),
    "Kryvansk": ("raid",),
    "Drutsk": ("adventure",),
}

"""Credentials for the Lavalink server."""
lava_creds = {
    "password": "password",
    "ws_url": "ws://127.0.0.1:2333",
    "rest_url": "http://127.0.0.1:2333",
}
query_endpoint = "http://localhost:7000/search"
resolve_endpoint = "http://localhost:7000/resolve"

"""This is the colour used in most embeds and for everything else. You know that yellow from somewhere ;)"""
primary_colour = 0xFFBC00

"""Our sentry URL to post bugs to."""
sentry_url = "https://whatever.sentry.url"

"""The redis PUBSUB channel used to communicate between processes"""
shard_announce_channel = "guild_channel"

"""The token used to interact with the raid backend."""
raidauth = "my raid api auth code"

"""Imgur token used for uploads."""
imgur_token = "my secret imgur token"

"""The Travitia API token."""
traviapi = "just a secret"

"""The Genius key."""
genius_key = "my key"

"""The base URL for links."""
base_url = "https://idlerpg.travitia.xyz"

"""The base URL for okapi (IdleRPG's image API)."""
okapi_url = "https://okapi.travitia.xyz"

"""The proxy URL."""
proxy_url = "http://my.proxy"
proxy_auth = "proxy-auth-key"

"""The Version of the Bot."""
version = "4.7.0a6"

"""Global cooldown (rate, per, [.user, .channel, .guild])"""
cooldown = commands.CooldownMapping.from_cooldown(1, 3, commands.BucketType.user)

"""Bronze donator cooldown (rate, per, [.user, .channel, .guild])"""
donator_cooldown = commands.CooldownMapping.from_cooldown(
    1, 2, commands.BucketType.user
)

"""Member role ID. Permissions will be overridden for this role during raids."""
member_role = 1234567890

"""Donator role order"""
donator_roles = [
    "Donators",
    "Designer",
    "Translator",
    "Nitro Booster",
    "Game Masters",
    "Code Redeemed",
    "Bronze Donators",
    "Silver Donators",
    "Gold Donators",
    "Emerald Donators",
    "Ruby Donators",
    "Diamond Donators",
]
donator_roles_short = [
    "basic",
    "basic",
    "basic",
    "basic",
    "basic",
    "basic",
    "bronze",
    "silver",
    "gold",
    "emerald",
    "ruby",
    "diamond",
]

"""Adventure times."""
adventure_times = {
    1: timedelta(hours=1),
    2: timedelta(hours=2),
    3: timedelta(hours=3),
    4: timedelta(hours=4),
    5: timedelta(hours=5),
    6: timedelta(hours=6),
    7: timedelta(hours=7),
    8: timedelta(hours=8),
    9: timedelta(hours=9),
    10: timedelta(hours=10),
    11: timedelta(hours=11),
    12: timedelta(hours=12),
    13: timedelta(hours=13),
    14: timedelta(hours=14),
    15: timedelta(hours=15),
    16: timedelta(hours=16),
    17: timedelta(hours=17),
    18: timedelta(hours=18),
    19: timedelta(hours=19),
    20: timedelta(hours=20),
    21: timedelta(hours=21),
    22: timedelta(hours=22),
    23: timedelta(hours=23),
    24: timedelta(hours=24),
    25: timedelta(hours=25),
    26: timedelta(hours=26),
    27: timedelta(hours=27),
    28: timedelta(hours=28),
    29: timedelta(hours=29),
    30: timedelta(hours=30),
}

adventure_names = {
    1: "Spider Cave",
    2: "Troll Bridge",
    3: "A Night Alone Outside",
    4: "Ogre Raid",
    5: "Proof Of Confidence",
    6: "Dragon Canyon",
    7: "Orc Tower",
    8: "Seamonster's Temple",
    9: "Dark Wizard's Castle",
    10: "Slay The Famous Dragon Arzagor",
    11: "Search For Excalibur",
    12: "Find Atlantis",
    13: "Tame A Phoenix",
    14: "Slay The Death Reaper",
    15: "Meet Adrian In Real Life",
    16: "The League Of Vecca",
    17: "The Gem Expedition",
    18: "Gambling Problems?",
    19: "The Necromancer Of Kord",
    20: "Last One Standing",
    21: "Gambling Problems? Again?",
    22: "Insomnia",
    23: "Illuminated",
    24: "Betrayal",
    25: "IdleRPG",
    26: "Learn Programming",
    27: "Scylla's Temple",
    28: "Trial Of Osiris",
    29: "Meet The War God In Hell",
    30: "Divine Intervention",
}

gods = {
    "Guilt": {
        "user": 1234567890,
        "description": (
            "Guilt is the goddess of suffering, obsession, misfortune, and wickedness."
            " Every evil act is said to originally be a thought in her head.  Many"
            " curse her name, but Guilt just smiles and continues to grow stronger from"
            " the misery--after all, happiness without hardship is no happiness at all."
        ),
        "boundaries": (0.0, 2.0),
    },
    "Tet": {
        "user": 1234567890,
        "description": (
            "Tet, god of play. Tired of seeing a world, where issues were resolved by"
            " war and violence, he introduced a new system where all trifles would be"
            " decided by games. But never mind that, let's have some fun now shall we."
        ),
        "boundaries": (0.8, 1.2),
    },
    "The Assassin": {
        "user": 1234567890,
        "description": (
            "Karmic retribution type. The judge, jury, and executioner. No one really"
            " knows of him or his real name. He is shrouded in mystery, but there are"
            " still those who offer to him to keep him at bay or to strike down their"
            " foes."
        ),
        "boundaries": (0.75, 1.25),
    },
    "Kvothe": {
        "user": 1234567890,
        "description": (
            "I have been called Kvothe the Bloodless, Kvothe the Arcane, and Kvothe"
            " Kingkiller. I have earned those names. Bought and paid for them. I have"
            " stolen princesses back from sleeping barrow kings. I have spent the night"
            " with Felurian and left with both my sanity and my life. I tread paths by"
            " moonlight that others fear to speak of during day. I have talked to Gods,"
            " loved women, and written songs that make the minstrels weep. You may have"
            " heard of me."
        ),
        "boundaries": (0.7, 1.3),
    },
    "Asmodeus": {
        "user": 1234567890,
        "description": (
            "Asmodeus, god of death. The reason adventurers don't die is because they"
            " give up their loot to him in order for them to live again. Their loot is"
            " the price they pay for a second chance."
        ),
        "boundaries": (0.7, 1.3),
    },
    "Salutations": {
        "user": 1234567890,
        "description": (
            "Known for excelling at greetings and making mutual relationships with"
            " every deity and also gaining followers due to his history/characteristic."
            " Despite his natural talent of mannerism and the swift making of"
            " relationships with not just gods, but humans as well, he is not to be"
            " easily fooled. Unironically, his most loyal follower is Cyberus, an"
            " ancient wolf general that has stood by and served him for the longest of"
            " times. Many fear Cyberus, but it only attacks when provoked or ordered to"
            " by Sal."
        ),
        "boundaries": (0.5, 1.5),
    },
    "War God Fox": {
        "user": 1234567890,
        "description": """And god said, there will be war!
        ...
        Do you see this mess on the battle field? It's my creation!
        If you survive in a war, you'll gain my respect. But, if you die in a war, you'll lose everything~

        Choose wisely my friend, maybe the next war will be against you.""",
        "boundaries": (0.5, 1.5),
    },
    "CHamburr": {
        "user": 1234567890,
        "description": (
            "Omniscient. Omnipotent. Omnipresent. An all-round god powered by endless"
            " streams of blood, with the one goal -- of flowing it through all mankind."
            " The day he was born, he promised to give his unexhaustive love equally to"
            " everyone..."
        ),
        "boundaries": (0.8, 1.2),
    },
    "Eden": {
        "user": 1234567890,
        "description": (
            "Eden is a goddess of sanctuary, protection and nature. People whisper"
            " prayers to her to keep them safe from danger and to find sanctuary from"
            " those who wish them harm. Her garden lays deep in the world filled with"
            " beauty and splendor. Those who seek it must travel into the depths of"
            " nature and pass the trails of the gatekeeper to enter."
        ),
        "boundaries": (0.5, 1.5),
    },
    "Jesus": {
        "user": 1234567890,
        "description": (
            "Sent from God to end the suffering and to bring light back where it is"
            " needed the most."
        ),
        "boundaries": (0.0, 2.0),
    },
}

classes = {
    "Warrior": [
        "Infanterist",
        "Footman",
        "Shieldbearer",
        "Knight",
        "Warmaster",
        "Templar",
        "Paladin",
    ],
    "Thief": ["Mugger", "Thief", "Rogue", "Bandit", "Chunin", "Renegade", "Assassin"],
    "Mage": [
        "Juggler",
        "Witcher",
        "Enchanter",
        "Mage",
        "Warlock",
        "Dark Caster",
        "White Sorcerer",
    ],
    "Paragon": [
        "Novice",
        "Proficient",
        "Artisan",
        "Master",
        "Champion",
        "Vindicator",
        "Paragon",
    ],
    "Ranger": ["Caretaker", "Tamer", "Trainer", "Bowman", "Hunter", "Warden", "Ranger"],
    "Raider": [
        "Adventurer",
        "Swordsman",
        "Fighter",
        "Swashbuckler",
        "Dragonslayer",
        "Raider",
        "Eternal Hero",
    ],
    "Ritualist": [
        "Priest",
        "Mysticist",
        "Doomsayer",
        "Seer",
        "Oracle",
        "Prophet",
        "Ritualist",
    ],
}

"""All item types ingame."""
item_types = [
    "Sword",
    "Shield",
    "Axe",
    "Wand",
    "Dagger",
    "Knife",
    "Spear",
    "Bow",
    "Hammer",
    "Scythe",
    "Howlet",
]
