"""
The IdleRPG Discord Bot
Copyright (C) 2018-2020 Diniboy and Gelbpunkt
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
import time

from datetime import timedelta
from json import dumps, loads
from typing import Union

import discord
import wavelink

from discord.ext import commands

from classes.converters import IntFromTo
from cogs.help import chunks


class VoteDidNotPass(commands.CheckFailure):
    pass


class Player(wavelink.Player):
    @property
    def position(self):
        if self.paused:
            return min(self.last_position, self.current.duration)

        difference = (time.time() * 1000) - self.last_update
        return min(self.last_position + difference, self.current.duration)

    def cleanup(self):
        self.loop = False
        self.locked = False
        self.dj = None
        self.eq = "Flat"


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
        ctx.player = ctx.bot.wavelink.get_player(ctx.guild.id, cls=Player)
        return True

    return commands.check(predicate)


def is_not_locked():
    def predicate(ctx):
        return (
            not getattr(ctx.player, "locked", False)
            or getattr(ctx.player, "dj", None) == ctx.author
        )

    return commands.check(predicate)


def is_dj():
    def predicate(ctx):
        return getattr(ctx.player, "dj", None) == ctx.author

    return commands.check(predicate)


def vote(action):
    async def predicate(ctx):
        if ctx.author == ctx.player.dj:
            return True
        if action == "skip":
            text = _(
                "{user} wants to skip a track. React if you agree. **{current}/{total}** voted for it!"
            )
        elif action == "pause_resume":
            text = _(
                "{user} wants to pause/resume the player. React if you agree. **{current}/{total}** voted for it!"
            )
        elif action == "stop":
            text = _(
                "{user} wants to stop playback. React if you agree. **{current}/{total}** voted for it!"
            )
        elif action == "volume":
            text = _(
                "{user} wants to change the volume. React if you agree. **{current}/{total}** voted for it!"
            )
        elif action == "loop":
            text = _(
                "{user} wants to toggle repeating. React if you agree. **{current}/{total}** voted for it!"
            )
        elif action == "equalizer":
            text = _(
                "{user} wants to change the equalizer. React if you agree. **{current}/{total}** voted for it!"
            )
        members = [
            m
            for m in ctx.bot.get_channel(int(ctx.player.channel_id)).members
            if m != ctx.guild.me
        ]
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
            accepted.add(u)
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
        _(
            """Query YouTube or SoundCloud for a track and play it or add it to the playlist."""
        )
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
            ctx.player.loop = False
            ctx.player.eq = "Flat"

        await self.add_entry_to_queue(track, ctx.player)

    @is_dj()
    @get_player()
    @is_in_vc()
    @commands.command(aliases=["unlock"])
    @locale_doc
    async def lock(self, ctx):
        _(
            """Lock/Unlock the player if you are the DJ. Allows noone else to control music."""
        )
        if ctx.player.locked:
            ctx.player.locked = False
        else:
            ctx.player.locked = True
        await ctx.message.add_reaction("✅")

    @vote("loop")
    @is_not_locked()
    @get_player()
    @is_in_vc()
    @commands.command(aliases=["repeat"])
    @locale_doc
    async def loop(self, ctx):
        _("""Toggle repeat of the current track.""")
        if ctx.player.loop:
            ctx.player.loop = False
        else:
            ctx.player.loop = True
        await ctx.message.add_reaction("✅")

    @vote("skip")
    @is_not_locked()
    @get_player()
    @is_in_vc()
    @commands.command()
    @locale_doc
    async def skip(self, ctx):
        _("""Skip the currently playing song.""")
        await ctx.player.stop()
        await ctx.message.add_reaction("✅")

    @vote("stop")
    @is_not_locked()
    @get_player()
    @is_in_vc()
    @commands.command(aliases=["leave"])
    @locale_doc
    async def stop(self, ctx):
        _("""Stops the music and leaves voice chat.""")
        await self.bot.redis.execute("DEL", f"{self.music_prefix}que:{ctx.guild.id}")
        await ctx.player.stop()
        await ctx.player.disconnect()
        ctx.player.cleanup()
        await ctx.message.add_reaction("✅")

    @vote("volume")
    @is_not_locked()
    @get_player()
    @is_in_vc()
    @commands.command(aliases=["vol"])
    @locale_doc
    async def volume(self, ctx, volume: IntFromTo(0, 100)):
        _("""Changes the playback's volume""")
        if volume > ctx.player.volume:
            vol_warn = await ctx.send(
                _(
                    ":warning:`Playback volume is going to change to {volume} in 5 seconds. To avoid the sudden earrape, control the volume on client side!`"
                ).format(volume=volume)
            )
            await asyncio.sleep(5)
            await ctx.player.set_volume(volume)
            await vol_warn.delete()
        else:
            await ctx.player.set_volume(volume)
        await ctx.send(
            _(":white_check_mark:` Volume successfully changed to {volume}!`").format(
                volume=volume
            ),
            delete_after=5,
        )

    @vote("pause_resume")
    @is_not_locked()
    @get_player()
    @is_in_vc()
    @commands.command(aliases=["resume"])
    @locale_doc
    async def pause(self, ctx):
        _("""Toggles the music playback's paused state""")
        if not ctx.player.paused:
            await ctx.player.set_pause(True)
            await ctx.send(_(":white_check_mark:`Song paused!`"), delete_after=5)
        else:
            await ctx.player.set_pause(False)
            await ctx.send(_(":white_check_mark:`Song resumed!`"), delete_after=5)

    @vote("equalizer")
    @is_not_locked()
    @get_player()
    @is_in_vc()
    @commands.command(aliases=["equaliser", "eq"])
    @locale_doc
    async def equalizer(self, ctx, eq: str.upper):
        _("""Sets the equalizer. May be flat, piano, metal or boost.""")
        if eq not in ctx.player.equalizers:
            return await ctx.send(
                _("Not a valid equalizer. May be flat, piano, metal or boost.")
            )
        await ctx.player.set_preq(eq)
        ctx.player.eq = eq.title()
        await ctx.message.add_reaction("✅")

    @get_player()
    @is_in_vc()
    @commands.command(aliases=["np"])
    @locale_doc
    async def now_playing(self, ctx):
        _("""Displays some information about the current song.""")
        current_song = self.load_track(
            loads(
                await self.bot.redis.execute(
                    "LINDEX", f"{self.music_prefix}que:{ctx.guild.id}", 0
                )
            )
        )

        if not (ctx.guild and ctx.author.color == discord.Color.default()):
            embed_color = ctx.author.color
        else:
            embed_color = self.bot.config.primary_colour

        playing_embed = discord.Embed(title=_("Now playing..."), colour=embed_color)
        playing_embed.add_field(
            name=_("Title"), value=f"```{current_song.title}```", inline=False
        )
        if (author := current_song.info.get("author")) :
            playing_embed.add_field(name=_("Uploader"), value=author)
        if current_song.length and not current_song.is_stream:
            try:
                playing_embed.add_field(
                    name=_("Length"), value=timedelta(milliseconds=current_song.length)
                )
                playing_embed.add_field(
                    name=_("Remaining"),
                    value=str(
                        timedelta(milliseconds=current_song.length)
                        - timedelta(milliseconds=ctx.player.position)
                    ).split(".")[0],
                )
                playing_embed.add_field(
                    name=_("Position"),
                    value=str(timedelta(milliseconds=ctx.player.position)).split(".")[
                        0
                    ],
                )
            except OverflowError:  # we cannot do anything if C cannot handle it
                pass
        elif current_song.is_stream:
            playing_embed.add_field(name=_("Length"), value="Live")
        else:
            playing_embed.add_field(name=_("Length"), value="N/A")
        text = _("Click me!")
        if current_song.uri:
            playing_embed.add_field(
                name=_("Link to the original"),
                value=f"**[{text}]({current_song.uri})**",
            )
        if current_song.thumb:
            playing_embed.set_thumbnail(url=current_song.thumb)
        playing_embed.add_field(name=_("Volume"), value=f"{ctx.player.volume} %")
        if ctx.player.paused:
            playing_embed.add_field(name=_("Playing status"), value=_("`⏸Paused`"))
        playing_embed.add_field(name=_("DJ"), value=ctx.player.dj.mention)
        playing_embed.add_field(
            name=_("Locked"), value=_("Yes") if ctx.player.locked else _("No")
        )
        playing_embed.add_field(
            name=_("Looping"), value=_("Yes") if ctx.player.loop else _("No")
        )
        playing_embed.add_field(name=_("Equalizer"), value=ctx.player.eq)
        if not current_song.is_stream:
            button_position = int(
                100 * (ctx.player.position / current_song.length) / 2.5
            )
            controller = (
                f"```ɴᴏᴡ ᴘʟᴀʏɪɴɢ: {current_song.title}\n"
                f"{(button_position - 1) * '─'}⚪{(40 - button_position) * '─'}\n ◄◄⠀{'▐▐' if not ctx.player.paused else '▶'} ⠀►►⠀⠀　　⠀ "
                f"{str(timedelta(milliseconds=ctx.player.position)).split('.')[0]} / {timedelta(seconds=int(current_song.length / 1000))}\n{11*' '}───○ 🔊⠀　　　ᴴᴰ ⚙ ❐ ⊏⊐```"
            )
            playing_embed.description = controller
        else:
            playing_embed.description = _("```No information```")
        if (
            user := ctx.guild.get_member(current_song.requester_id)
        ) :  # check to avoid errors on guild leave
            playing_embed.set_footer(
                text=_("Song requested by: {user}").format(user=user.display_name),
                icon_url=user.avatar_url_as(format="png", size=64),
            )
        await ctx.send(embed=playing_embed)

    @get_player()
    @is_in_vc()
    @commands.command(aliases=["q", "que", "cue"])
    @locale_doc
    async def queue(self, ctx):
        _("""Show the next (maximum 5) tracks in the queue.""")
        entries = await self.bot.redis.execute(
            "LRANGE", f"{self.music_prefix}que:{ctx.guild.id}", 1, 5
        )
        if entries:
            paginator = commands.Paginator()
            for entry in entries:
                entry = self.load_track(loads(entry))
                paginator.add_line(
                    f"• {entry.title} ({timedelta(milliseconds=entry.length)}) "
                    f"- {ctx.guild.get_member(entry.requester_id).display_name}"
                )
            queue_length = await self.get_queue_length(ctx.guild.id) - 1
            text = _("Upcoming entries")
            await ctx.send(
                embed=discord.Embed(
                    title=f"{text} ({len(entries)}/{queue_length})",
                    description=paginator.pages[0],
                    color=discord.Color.gold(),
                )
            )
        else:
            await ctx.send(_(":warning:`No more entries left.`"))

    @commands.command()
    @locale_doc
    async def lyrics(self, ctx, *, query: str = None):
        _(
            """Retrieves song lyrics. If no song specified, will check the current playing song."""
        )
        if query is None and ctx.guild:
            track = self.bot.wavelink.get_player(ctx.guild.id, cls=Player).current
            if not track:
                return await ctx.send(
                    _("I am not playing. Please specify a song to look for.")
                )
            query = track.title
        elif query is None and not ctx.guild:
            return await ctx.send(_("Please specify a song."))
        elif len(query) < 3:
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
        if not player.loop:
            await self.bot.redis.execute(
                "LPOP", f"{self.music_prefix}que:{player.guild_id}"
            )  # remove the previous entry
        if (
            not await self.get_queue_length(player.guild_id)
            or len(self.bot.get_channel(int(player.channel_id)).members) == 1
        ):
            # That was the last track
            await player.disconnect()
            player.cleanup()
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
