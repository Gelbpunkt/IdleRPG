"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt
This program is free software: you can redistribute it and/or modify

it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
import asyncio

from json import dumps, loads
from typing import Union

import wavelink

from discord.ext import commands

from cogs.help import chunks


class VoteDidNotPass(commands.CheckFailure):
    pass


def is_in_vc():
    def predicate(ctx):
        try:
            ctx.voice_channel = ctx.author.voice.channel.id
        except AttributeError:
            return False
        return True

    return commands.check(predicate)


def get_player():
    def predicate(ctx):
        ctx.player = ctx.bot.wavelink.get_player(ctx.guild.id)
        return True

    return commands.check(predicate)


def is_not_locked():
    def predicate(ctx):
        return not getattr(ctx.player, "locked", False) or getattr(ctx.player, "dj", None) == ctx.author

    return commands.check(predicate)


def vote(action):
    async def predicate(ctx):
        if ctx.author == ctx.player.dj:
            return True
        if action == "skip":
            text = _(
                "{user} wants to skip a track. React if you agree. **{current}/{total}** voted for it!"
            )
        members = ctx.bot.get_channel(ctx.player.channel_id).members
        accepted = {ctx.author}
        needed = int(len(members) / 2) + 1

        msg = await ctx.send(
            text.format(user=ctx.author.mention, current=len(accepted), total=needed)
        )

        def check(r, u):
            return (
                u in members
                and u not in accepted
                and str(r.emoji) == "\U00002705"
                and r.message.id == msg.id
            )

        await msg.add_reaction("\U00002705")

        while len(accepted) < needed:
            try:
                r, u = await ctx.bot.wait_for("reaction_add", check=check, timeout=10)
            except asyncio.TimeoutError:
                raise VoteDidNotPass()
            accepted.append(u)
            await msg.edit(
                content=text.format(
                    user=ctx.author.mention, current=len(accepted), total=needed
                )
            )

        await msg.delete()
        await ctx.send(_("Vote passed!"))
        return True

    return commands.check(predicate)


class FakeTrack(wavelink.Track):
    __slots__ = (
        "id",
        "info",
        "query",
        "title",
        "ytid",
        "length",
        "duration",
        "uri",
        "is_stream",
        "dead",
        "thumb",
        "requester_id",
        "channel_id",
    )

    def __init__(self, *args, **kwargs):
        self.requester_id = kwargs.pop("requester_id", None)
        self.channel_id = kwargs.pop("channel_id", None)
        super().__init__(*args, **kwargs)


class Music2(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.music_prefix = "mp:idle2:" if not bot.config.is_beta else "mp:idlebeta2:"

        if not hasattr(self.bot, "wavelink"):
            self.bot.wavelink = wavelink.Client(self.bot)

        self.bot.loop.create_task(self.connect())

    async def connect(self):
        await self.bot.wait_until_ready()
        node = await self.bot.wavelink.initiate_node(**self.bot.config.lava_creds_new)
        node.set_hook(self.event_hook)

    @is_not_locked()
    @get_player()
    @is_in_vc()
    @commands.command(aliases=["scsearch"])
    @locale_doc
    async def play(self, ctx, *, query: str):
        _("""Query YouTube or SoundCloud for a track and play it or add it to the playlist.""")
        if ctx.invoked_with == "scsearch":
            pre = "scsearch:"
        else:
            pre = "ytsearch:"
        try:
            tracks = await self.bot.wavelink.get_tracks(f"{pre}{query}")
            track = tracks[0] if isinstance(tracks, list) else tracks.tracks[0]
            del tracks
            track = self.update_track(
                track, requester_id=ctx.author.id, channel_id=ctx.channel.id
            )
        except IndexError:
            return await ctx.send(_("No results..."))

        if not ctx.player.is_connected:
            await ctx.player.connect(ctx.voice_channel)
            # Setup some attributes
            ctx.player.dj = ctx.author
            ctx.player.locked = False

        await self.add_entry_to_queue(track, ctx.player)

    @vote("skip")
    @is_not_locked()
    @get_player()
    @is_in_vc()
    @commands.commanx()
    @locale_doc
    async def skip(self, ctx):
        _("""Skip the currently playing song.""")
        await ctx.player.stop()
        await ctx.message.add_reaction("✅")

    @commands.command()
    @locale_doc
    async def lyrics(self, ctx, *, query: str):
        _("""Retrieves song lyrics.""")
        if len(query) < 3:
            return await ctx.send(_(":x: Look for a longer query!"), delete_after=5)

        headers = {"Authorization": f"Bearer {self.bot.config.ksoft_key}"}
        params = {"q": query, "limit": 1}
        async with self.bot.session.get(
            "https://api.ksoft.si/lyrics/search", params=params, headers=headers
        ) as req:
            if req.status != 200:
                return await ctx.send(_(":warning: No results!"))
            json_data = loads(await req.text())
        if not json_data.get("data", []):
            return await ctx.send(_(":warning: No results!"))
        result = json_data["data"][0]
        del json_data
        p = commands.Paginator()
        for l in result.get("lyrics", _("No lyrics found!")).split("\n"):
            for i in chunks(l, 1900):
                p.add_line(i)
        await self.bot.paginator.Paginator(
            title=f"{result.get('artist', _('Unknown Artist'))} - {result.get('name', _('Unknown Title'))}",
            entries=p.pages,
            length=1,
        ).paginate(ctx)

    def update_track(self, track: wavelink.Track, requester_id: int, channel_id: int):
        return FakeTrack(
            track.id,
            track.info,
            query=track.query,
            requester_id=requester_id,
            channel_id=channel_id,
        )

    def serialize_track(self, track: FakeTrack):
        """Serializes a track to a dict."""
        return {
            "id": track.id,
            "info": track.info,
            "query": track.query,
            "title": track.title,
            "ytid": track.ytid,
            "length": track.length,
            "duration": track.duration,
            "uri": track.uri,
            "is_stream": track.is_stream,
            "dead": track.dead,
            "thumb": track.thumb,
            "requester_id": track.requester_id,
            "channel_id": track.channel_id,
        }

    def load_track(self, track: dict):
        return FakeTrack(
            track["id"],
            track["info"],
            query=track["query"],
            requester_id=track["requester_id"],
            channel_id=track["channel_id"],
        )

    async def add_entry_to_queue(self, track: FakeTrack, player: wavelink.Player):
        """Plays a song or adds to the queue"""
        if not await self.get_queue_length(player.guild_id):
            await self.bot.redis.execute(
                "RPUSH",
                f"{self.music_prefix}que:{player.guild_id}",
                dumps(self.serialize_track(track)),
            )
            await self.play_track(track, player)
        else:
            await self.bot.redis.execute(
                "RPUSH",
                f"{self.music_prefix}que:{player.guild_id}",
                dumps(self.serialize_track(track)),
            )
            zws = "@\u200b"
            await self.bot.get_channel(track.channel_id).send(
                _("🎧 Added {title} to the queue...").format(
                    title=track.title.replace("@", zws)
                )
            )

    async def play_track(self, track: FakeTrack, player: wavelink.Player):
        zws = "@\u200b"
        await self.bot.get_channel(track.channel_id).send(
            _("🎧 Playing {title}...").format(title=track.title.replace("@", zws))
        )
        await player.play(track)

    async def get_queue_length(self, guild_id: int) -> Union[int, bool]:
        """Returns the queue's length or False if there is no upcoming songs"""
        query_length = await self.bot.redis.execute(
            "LLEN", f"{self.music_prefix}que:{guild_id}"
        )
        if not query_length or query_length > 0:
            return query_length
        else:
            return False

    async def on_track_end(self, player: wavelink.Player):
        await self.bot.redis.execute(
            "LPOP", f"{self.music_prefix}que:{player.guild_id}"
        )  # remove the previous entry
        if not await self.get_queue_length(player.guild_id):
            # That was the last track
            await player.disconnect()
            await self.bot.redis.execute(
                "DEL", f"{self.music_prefix}que:{player.guild_id}"
            )
        else:
            await self.play_track(
                self.load_track(
                    loads(
                        await self.bot.redis.execute(
                            "LINDEX", f"{self.music_prefix}que:{player.guild_id}", 0
                        )
                    )
                ),
                player,
            )

    async def event_hook(self, event):
        """Handle wavelink events"""
        if isinstance(event, wavelink.TrackEnd):
            await self.on_track_end(event.player)

    async def cleanup(self):
        for player in self.bot.wavelink.players.values():
            await player.stop()
            await player.disconnect()
        queue_keys = await self.bot.redis.execute("KEYS", "{self.music_prefix}que:*")
        if queue_keys:
            await self.bot.redis.execute("DEL", *[key for key in queue_keys])

    def cog_unload(self):
        self.bot.queue.put_nowait(self.cleanup())


def setup(bot):
    bot.add_cog(Music2(bot))
