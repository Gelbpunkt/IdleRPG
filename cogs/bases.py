import asyncio
import contextlib
import discord
import enum
import functools
import inspect
import random

from discord.ext import commands


class Status(enum.Enum):
    PLAYING = enum.auto()
    END = enum.auto()
    TIMEOUT = enum.auto()
    QUIT = enum.auto()


class _TwoPlayerWaiter:
    def __init__(self, author, recipient):
        self._author = author
        self._recipient = recipient
        self._future = None
        self._closer = None
        self._event = asyncio.Event()

    def wait(self):
        future = self._future
        if future is None:
            future = self._future = asyncio.ensure_future(
                asyncio.wait_for(self._event.wait(), timeout=300)
            )
        return future

    def confirm(self, member):
        if self._author == member:
            raise RuntimeError(
                "You can't join a game that you've created. Are you really that lonely?"
            )

        if self._recipient is None:
            self._recipient = member

        elif member != self._recipient:
            raise RuntimeError("This game is not for you!")

        self._event.set()

    def decline(self, member):
        if self._recipient != member:
            return False

        self._closer = member
        return self._future.cancel()

    def cancel(self, member):
        if self._author != member:
            return False

        self._closer = member
        return self._future.cancel()

    def done(self):
        return bool(self._future and self._future.done())


class NoSelfArgument(commands.BadArgument):
    """Exception raised in CheckedMember when the author passes themself as an argument"""


class _MemberConverter(commands.MemberConverter):
    async def convert(self, ctx, arg):
        member = await super().convert(ctx, arg)
        if member.status is discord.Status.offline:
            raise commands.BadArgument(f"{member} is offline.")
        if member.bot:
            raise commands.BadArgument(f"{member} is a bot. You can't use a bot here.")
        if member == ctx.author:
            raise NoSelfArgument("You can't use yourself. lol.")

        return member

    @staticmethod
    def random_example(ctx):
        members = [
            member
            for member in ctx.guild.members
            if member.status is not discord.Status.offline
            and not member.bot
            and member != ctx.author
        ]
        member = random.choice(members) if members else "SomeGuy"
        return f"@{member}"


@contextlib.contextmanager
def _swap_item(obj, item, new_val):
    obj[item] = new_val
    try:
        yield
    finally:
        if item in obj:
            del obj[item]


@contextlib.contextmanager
def _dummy_cm(*args, **kwargs):
    yield


class TwoPlayerGameCog:
    def __init__(self, bot):
        self.bot = bot
        self.running_games = {}
        self._invited_games = {}

    def __init_subclass__(cls, *, game_cls, name=None, cmd=None, aliases=(), **kwargs):
        super().__init_subclass__(**kwargs)

        cls.name = name or cls.__name__
        cls.__game_class__ = game_cls
        cmd_name = cmd or cls.__name__.lower()

        group_help = inspect.getdoc(cls._game).format(name=cls.name)
        # We can't use the decorator because all the check decorator does is
        # add the predicate to an attribute called __commands_checks__, which
        # gets deleted after the first command.
        group = commands.group(
            name=cmd_name, aliases=aliases, help=group_help, invoke_without_command=True
        )
        group_command = group(commands.bot_has_permissions(embed_links=True)(cls._game))
        setattr(cls, f"{cmd_name}", group_command)

        gc = group_command.command
        for name, member in inspect.getmembers(cls):
            if not name.startswith("_game_"):
                continue

            name = name[6:]

            help = inspect.getdoc(member).format(name=cls.name, cmd=cmd_name)
            command = gc(name=name, help=help)(member)
            setattr(cls, f"{cmd_name}_{name}", command)

        setattr(cls, f"_{cls.__name__}__error", cls._error)

    async def _error(self, ctx, error):
        if isinstance(error, NoSelfArgument):
            message = random.choice(
                (
                    "Don't play with yourself. x3",
                    "You should mention someone else over there. o.o",
                    "Self inviting, huh... :eyes:",
                )
            )
            await ctx.send(message)

    def _create_invite(self, ctx, member):
        if member:
            action = "invited you to"
            description = (
                "**Do you accept?**\n"
                f"Yes: Type `` {ctx.prefix}{ctx.command.root_parent or ctx.command} join``\n"
                f"No: Type `` {ctx.prefix}{ctx.command.root_parent or ctx.command} decline``\n"
                "You have 5 minutes."
            )
        else:
            action = "created"
            description = (
                f"Type `{ctx.prefix}{ctx.command.root_parent or ctx.command} join` to join in!\n"
                "This will expire in 5 minutes."
            )

        title = f"{ctx.author} has {action} a game of {self.__class__.name}!"
        return (
            discord.Embed(colour=0x00FF00, description=description)
            .set_author(name=title)
            .set_thumbnail(url=ctx.author.avatar_url)
        )

    async def _invite_member(self, ctx, member):
        invite_embed = self._create_invite(ctx, member)

        if member is None:
            await ctx.send(embed=invite_embed)
        else:
            await ctx.send(
                f"{member.mention}, you have a challenger!", embed=invite_embed
            )

    async def _end_game(self, ctx, inst, result):
        if result.winner is None:
            return await ctx.send("It looks like nobody won :(")

        user = result.winner.user
        winner_embed = (
            discord.Embed(
                colour=0x00FF00,
                description=f"Game took {result.turns} turns to complete.",
            )
            .set_thumbnail(url=user.avatar_url)
            .set_author(name=f"{user} is the winner!")
        )

        await ctx.send(embed=winner_embed)

    async def _game(self, ctx, *, member: _MemberConverter = None):
        """Starts a game of {name}

        You can specify a user to invite them to play with
        you. Leaving out the user creates a game that anyone
        can join.
		Credits to MIlkusaba#4553
        """

        if ctx.channel.id in self.running_games:
            return await ctx.send(
                f"There's a {self.__class__.name} game already running in this channel..."
            )

        if member is not None:
            pair = (ctx.author.id, member.id)
            channel_id = self._invited_games.get(pair)
            if channel_id:
                return await ctx.send(
                    "Um, you've already invited them in "
                    f"<#{channel_id}>, please don't spam them.."
                )

            cm = _swap_item(self._invited_games, pair, ctx.channel.id)
        else:
            cm = _dummy_cm()

        put_in_running = functools.partial(
            _swap_item, self.running_games, ctx.channel.id
        )

        # await ctx.release()
        with cm:
            await self._invite_member(ctx, member)
            with put_in_running(_TwoPlayerWaiter(ctx.author, member)):
                waiter = self.running_games[ctx.channel.id]
                try:
                    await waiter.wait()
                except asyncio.TimeoutError:
                    if member:
                        return await ctx.send(
                            f"{member.mention} couldn't join in time... :/"
                        )
                    else:
                        return await ctx.send("No one joined in time. :(")
                except asyncio.CancelledError:
                    if waiter._closer == ctx.author:
                        msg = f"{ctx.author.mention} has closed the game. False alarm everyone..."
                    else:
                        msg = f"{ctx.author.mention}, {member} declined your challenge. :("
                    return await ctx.send(msg)

            with put_in_running(self.__game_class__(ctx, waiter._recipient)):
                inst = self.running_games[ctx.channel.id]
                result = await inst.run()

            await self._end_game(ctx, inst, result)

    async def _game_join(self, ctx):
        """Joins a {name} game.

        This either must be for you, or for everyone.
        """

        waiter = self.running_games.get(ctx.channel.id)
        if waiter is None:
            return await ctx.send(
                f"There's no {self.__class__.name} for you to join..."
            )

        if not isinstance(waiter, _TwoPlayerWaiter):
            return await ctx.send("Sorry... you were late. ;-;")

        try:
            waiter.confirm(ctx.author)
        except RuntimeError as e:
            await ctx.send(e)
        else:
            await ctx.send(f"Alright {ctx.author.mention}, good luck!")

    async def _game_decline(self, ctx):
        """Declines a {name} game.

        This game must be for you. (i.e. through `{cmd} @user`)
        """

        waiter = self.running_games.get(ctx.channel.id)
        if waiter is None:
            return await ctx.send(
                f"There's no {self.__class__.name} for you to decline..."
            )

        if isinstance(waiter, _TwoPlayerWaiter) and waiter.decline(ctx.author):
            with contextlib.suppress(discord.HTTPException):
                await ctx.message.add_reaction("\U00002705")

    async def _game_close(self, ctx):
        """Closes a {name} game, stopping anyone from joining.

        You must be the creator of the game.
        """
        waiter = self.running_games.get(ctx.channel.id)
        if waiter is None:
            return await ctx.send(
                f"There's no {self.__class__.name} for you to decline..."
            )

        if isinstance(waiter, _TwoPlayerWaiter) and waiter.cancel(ctx.author):
            with contextlib.suppress(discord.HTTPException):
                await ctx.message.add_reaction("\U00002705")
