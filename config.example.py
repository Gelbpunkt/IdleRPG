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
    "cogs.admin",
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
    "cogs.error_handler",
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
]

"""The channel where vote logging is sent from. This is an ID."""
upvote_channel = 453_948_653_913_112_609

"""The prefix to use if none is set custom or we are in DMs."""
global_prefix = "$"

"""The channel ID to send join logs to."""
join_channel = 441_821_532_696_870_922

"""Defines whether it is a beta version or not. This would disable some parts, e.g. no longer post the stats to DBL and BFD."""
is_beta = False

"""A list of Admins by ID."""
admins = [
    356_091_260_429_402_122,
    373_797_591_395_205_122,
    395_938_979_293_167_617,
    270_624_053_809_643_522,
    222_005_168_147_922_944,
    147_874_400_836_911_104,
    278_269_289_960_833_035,
    291_215_916_916_801_536,
    213_045_557_181_022_209,
    210_510_122_810_605_569,
    294_894_701_708_967_936,
    254_234_402_354_233_344,
    340_745_895_932_854_272,
    438_443_378_498_338_816,
    525_139_442_663_424_011,
    322_354_047_162_122_243,
    300_088_143_422_685_185,
    353_978_827_157_929_987,
    266_845_673_176_039_424,
]

"""A list of banned users."""
bans = [
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

"""The support server ID."""
support_server_id = 430_017_996_304_678_923

"""A channel ID to send admin logs to."""
admin_log_channel = 457_197_748_626_653_184

"""Credentials for the Lavalink server."""
lava_creds = {
    "password": "password",
    "ws_url": "ws://127.0.0.1:2333",
    "rest_url": "http://127.0.0.1:2333",
}

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

"""The KSoft key."""
ksoft_key = "my key"

"""The base URL for links."""
base_url = "https://idlerpg.travitia.xyz"

"""The base URL for okapi (IdleRPG's image API)."""
okapi_url = "https://okapi.travitia.xyz"

"""The Version of the Bot."""
version = "4.1.5"

"""Global cooldown (rate, per, [.user, .channel, .guild])"""
cooldown = commands.CooldownMapping.from_cooldown(1, 3, commands.BucketType.user)


"""Adventure times."""
adventure_times = {
    1: timedelta(minutes=30),
    2: timedelta(hours=1),
    3: timedelta(hours=2),
    4: timedelta(hours=3),
    5: timedelta(hours=4),
    6: timedelta(hours=5),
    7: timedelta(hours=6),
    8: timedelta(hours=7),
    9: timedelta(hours=8),
    10: timedelta(hours=9),
    11: timedelta(hours=10),
    12: timedelta(hours=11),
    13: timedelta(hours=12),
    14: timedelta(hours=13),
    15: timedelta(hours=14),
    16: timedelta(hours=15),
    17: timedelta(hours=16),
    18: timedelta(hours=17),
    19: timedelta(hours=18),
    20: timedelta(hours=19),
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
}

gods = {
    "Guilt": {
        "user": 463318425901596672,
        "description": "Guilt is the goddess of suffering, obsession, misfortune, and wickedness. Every evil act is said to originally be a thought in her head.  Many curse her name, but Guilt just smiles and continues to grow stronger from the misery--after all, happiness without hardship is no happiness at all.",
    },
    "Gambit": {
        "user": 402603953453268992,
        "description": "A mercurial god, though not purposefully evil. As the god of chance and risk, Gambit is the patron of gamblers, thieves, and adventurers.  If you succeed in a risky venture, he is said to have smirked with amusement at your attempt.  However, dealing with him is like flipping a coin--which side will it be?",
    },
    "The Assassin": {
        "user": 294894701708967936,
        "description": "Karmic retribution type. The judge, jury, and executioner. No one really knows of him or his real name. He is shrouded in mystery, but there are still those who offer to him to keep him at bay or to strike down their foes.",
    },
    "Kvothe": {
        "user": 489637665633730560,
        "description": "I have been called Kvothe the Bloodless, Kvothe the Arcane, and Kvothe Kingkiller. I have earned those names. Bought and paid for them. I have stolen princesses back from sleeping barrow kings. I have spent the night with Felurian and left with both my sanity and my life. I tread paths by moonlight that others fear to speak of during day. I have talked to Gods, loved women, and written songs that make the minstrels weep. You may have heard of me.",
    },
    "Asmodeus": {
        "user": 318824057158107137,
        "description": "Asmodeus, god of death. The reason adventurers don't die is because they give up their loot to him in order for them to live again. Their loot is the price they pay for a second chance.",
    },
    "Salutations": {
        "user": 344227184438804480,
        "description": "Known for excelling at greetings and making mutual relationships with every deity and also gaining followers due to his history/characteristic. Despite his natural talent of mannerism and the swift making of relationships with not just gods, but humans as well, he is not to be easily fooled. Unironically, his most loyal follower is Cyberus, an ancient wolf general that has stood by and served him for the longest of times. Many fear Cyberus, but it only attacks when provoked or ordered to by Sal.",
    },
    "War God Fox": {
        "user": 254234402354233344,
        "description": """And god said, there will be war!
        ...
        Do you see this mess on the battle field? It's my creation!
        If you survive in a war, you'll gain my respect. But, if you die in a war, you'll lose everything~

        Choose wisely my friend, maybe the next war will be against you.""",
    },
    "Athena, Goddess of Wisdom": {
        "user": 226038728211038208,
        "description": "Goddess of wisdom, war and the crafts, and favourite daughter of Zeus, Athena was, perhaps, the wisest, most courageous, and certainly the most resourceful of the Olympian gods. Follow in her footsteps and become a follower to live through this wretched mayhem. As she is not only wise, but a powerful Leader. You do not want to her have her as your enemy now, Do you?",
    },
    "CHamburr": {
        "user": 446290930723717120,
        "description": "Omniscient. Omnipotent. Omnipresent. An all-round god powered by endless streams of blood, with the one goal -- of flowing it through all mankind. The day he was born, he promised to give his unexhaustive love equally to everyone...",
    },
    "Ananke": {
        "user": 373797591395205122,
        "description": """Goddess of inevitability, compulsion, and necessity.
        Nothing exists without its other "weight" and Namara: Shadow and Light, Rise and Fall, etc.
        Follow to get fair rewards, and never be betrayed.""",
    },
    "Jesus": {
        "user": 322354047162122243,
        "description": "Sent from God to end the suffering and to bring light back where it is needed the most.",
    },
}
