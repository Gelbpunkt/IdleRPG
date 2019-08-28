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
from datetime import timedelta
from functools import partial
from json import dumps, loads
from random import choice
from re import search as re_search
from typing import Union

import discord
import pylava
from discord.ext import commands


# Exceptions
class NotInVoiceChannel(commands.CheckFailure):
    """Should be raised if the invoker isn't in a voice channel"""

    pass


class MusicPlayer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.music_prefix = "mp:idle:" if not bot.config.is_beta else "mp:idlebeta"
        if not hasattr(bot, "lava") or not bot.lava.connected:
            bot.queue.put_nowait(self.initialize_connection())

    # Commands
    @commands.guild_only()
    @commands.command()
    @locale_doc
    async def play(self, ctx, *, query: str):
        _("""Play some tunes""")
        player = self.bot.lava.get_player(ctx.guild.id)
        if not (
            query.startswith("https://")
            or query.startswith("http://")
            or query.startswith("youtu")
            or query.startswith("soundcloud")
        ):
            # if it isn't a link, we try to look for YT results
            results = (await player.query(f"ytsearch:{query.replace(' ', '+')}")).get(
                "tracks"
            )
        else:
            # if it is a link, we need to do a simple query
            results = (await player.query(query.replace(" ", "+"))).get("tracks")
        if results:
            result = results[0]
        else:
            return await ctx.send(_(":warning:`No results...`"), delete_after=5)
        del results  # memleak avoiding
        if ctx.author.voice:
            await player.connect(ctx.author.voice.channel.id)
        else:
            return await ctx.send(_(":warning:`Connect to a voice channel first!`"))
        result["requester_id"] = ctx.author.id
        result["channel_id"] = ctx.channel.id  # additional informations to keep
        await self.add_entry_to_queue(result, player)
        player.track_callback = self.on_track_end

    @commands.guild_only()
    @commands.command()
    @locale_doc
    async def scsearch(self, ctx, *, query: str):
        _("""Search and play some tunes from SoundCloud""")
        player = self.bot.lava.get_player(ctx.guild.id)
        results = (await player.query(f"scsearch:{query.replace(' ', '+')}")).get(
            "tracks"
        )
        if results:
            result = results[0]
        else:
            return await ctx.send(_(":warning:`No results...`"), delete_after=5)
        del results  # memleak avoiding
        if ctx.author.voice:
            await player.connect(ctx.author.voice.channel.id)
        else:
            return await ctx.send(_(":warning:`Connect to a voice channel first!`"))
        result["requester_id"] = ctx.author.id
        result["channel_id"] = ctx.channel.id  # additional information to keep
        await self.add_entry_to_queue(result, player)
        player.track_callback = self.on_track_end

    @commands.guild_only()
    @commands.command(aliases=["pran", "pr", "rp", "randomplay", "ranp", "randomp"])
    @locale_doc
    async def playrandom(self, ctx, *, query: str):
        _("""Picks a random result, and plays for you""")
        player = self.bot.lava.get_player(ctx.guild.id)
        if not (
            query.startswith("https://")
            or query.startswith("http://")
            or query.startswith("youtu")
            or query.startswith("soundcloud")
        ):
            # if it isn't a link, we try to look for YT results
            results = (await player.query(f"ytsearch:{query.replace(' ', '+')}")).get(
                "tracks"
            )
        else:
            # if it is a link, we need to do a simple query
            results = (await player.query(query.replace(" ", "+"))).get("tracks")
        if results:
            result = choice(results)
        else:
            return await ctx.send(_(":warning:`No results...`"), delete_after=5)
        del results  # memleak avoiding
        if ctx.author.voice:
            await player.connect(ctx.author.voice.channel.id)
        else:
            return await ctx.send(_(":warning:`Connect to a voice channel first!`"))
        result["requester_id"] = ctx.author.id
        result["channel_id"] = ctx.channel.id  # additional informations to keep
        await self.add_entry_to_queue(result, player)
        player.track_callback = self.on_track_end

    @commands.guild_only()
    @commands.command(aliases=["stop"])
    @locale_doc
    async def leave(self, ctx):
        _("""Stops the music and leaves the channel""")
        player = self.bot.lava.get_player(ctx.guild.id)
        if player.connected or ctx.guild.me.voice:
            player.track_callback = None  # don't need to handle it twice
            await self.bot.redis.execute(
                "DEL", f"{self.music_prefix}que:{ctx.guild.id}"
            )
            await player.stop()
            await player.disconnect()
            await ctx.send(_(":white_check_mark:` Done!`"), delete_after=5)
        else:
            await ctx.send(
                _(
                    ":warning:`I am currently not connected to any channel in this guild...`"
                ),
                delete_after=5,
            )

    @commands.guild_only()
    @commands.command(aliases=["q", "que", "cue"])
    @locale_doc
    async def queue(self, ctx):
        _("""Show the next (maximum 5) tracks in the queue""")
        entries = await self.bot.redis.execute(
            "LRANGE", f"{self.music_prefix}que:{ctx.guild.id}", 1, 5
        )
        if entries:
            paginator = commands.Paginator()
            for entry in entries:
                entry = loads(entry)
                paginator.add_line(
                    f'• {entry.get("info").get("title")} ({timedelta(milliseconds=entry.get("info").get("length"))}) '
                    f'- {ctx.guild.get_member(entry.get("requester_id")).display_name}'
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

    @commands.guild_only()
    @commands.command()
    @locale_doc
    async def skip(self, ctx):
        _("""Skips the current song""")
        player = self.bot.lava.get_player(ctx.guild.id)
        if player.paused or player.playing:
            await player.stop()
            await ctx.message.add_reaction("✅")
        else:
            await ctx.send(_(":warning:`Nothing to skip...`"), delete_after=5)

    @commands.guild_only()
    @commands.command(name="volume", aliases=["vol"])
    @locale_doc
    async def _volume(self, ctx, volume: int):
        _("""Changes the playback's volume""")
        player = self.bot.lava.get_player(ctx.guild.id)
        if not (player.paused or player.playing):
            return await ctx.send(
                _(":warning:`I am currently not playing anything here...`"),
                delete_after=5,
            )
        if not 0 <= volume <= 100:
            return await ctx.send(
                _(":warning:`The volume must between 0 and 100!`"), delete_after=5
            )
        if volume > player.volume:
            vol_warn = await ctx.send(
                _(
                    ":warning:`Playback volume is going to change to {volume} in 5 seconds. To avoid the sudden earrape, control the volume on client side!`"
                ).format(volume=volume)
            )
            await asyncio.sleep(5)
            await player.set_volume(volume)
            await vol_warn.delete()
        else:
            await player.set_volume(volume)
        await ctx.send(
            _(":white_check_mark:` Volume successfully changed to {volume}!`").format(
                volume=volume
            ),
            delete_after=5,
        )

    @commands.guild_only()
    @commands.command(aliases=["resume"])
    @locale_doc
    async def pause(self, ctx):
        _("""Toggles the music playback's paused state""")
        player = self.bot.lava.get_player(ctx.guild.id)
        if player.playing and not player.paused:
            await player.set_pause(True)
            await ctx.send(_(":white_check_mark:`Song paused!`"), delete_after=5)
        elif player.paused:
            await player.set_pause(False)
            await ctx.send(_(":white_check_mark:`Song resumed!`"), delete_after=5)
        elif not player.paused and not player.playing:
            await ctx.send(_(":warning:`The song list is empty!`"), delete_after=5)

    @commands.guild_only()
    @commands.command(aliases=["np"])
    @locale_doc
    async def now_playing(self, ctx):
        _("""Displays some information about the current song""")
        player = self.bot.lava.get_player(ctx.guild.id)
        current_song = await self.bot.redis.execute(
            "LINDEX", f"{self.music_prefix}que:{ctx.guild.id}", 0
        )
        if not current_song:
            return await ctx.send(
                _(":warning:`I'm not playing anything at the moment...`"),
                delete_after=5,
            )
        current_song = loads(current_song)
        if not (ctx.guild and ctx.author.color == discord.Color.default()):
            embed_color = ctx.author.color
        else:
            embed_color = self.bot.config.primary_colour
        player = self.bot.lava.get_player(ctx.guild.id)
        playing_embed = discord.Embed(title=_("Now playing..."), colour=embed_color)
        if current_song.get("info"):
            if current_song["info"].get("title"):
                playing_embed.add_field(
                    name=_("Title"),
                    value=f'```{current_song["info"]["title"]}```',
                    inline=False,
                )
            if current_song["info"].get("author"):
                playing_embed.add_field(
                    name=_("Uploader"), value=current_song["info"]["author"]
                )
            if current_song["info"].get("length") and not current_song["info"].get(
                "isStream"
            ):
                try:
                    playing_embed.add_field(
                        name=_("Length"),
                        value=timedelta(milliseconds=current_song["info"]["length"]),
                    )
                    playing_embed.add_field(
                        name=_("Remaining"),
                        value=str(
                            timedelta(milliseconds=current_song["info"]["length"])
                            - timedelta(seconds=player.position)
                        ).split(".")[0],
                    )
                    playing_embed.add_field(
                        name=_("Position"),
                        value=str(timedelta(seconds=player.position)).split(".")[0],
                    )
                except OverflowError:  # we cannot do anything if C cannot handle it
                    pass
            elif current_song["info"].get("isStream"):
                playing_embed.add_field(name=_("Length"), value="Live")
            else:
                playing_embed.add_field(name=_("Length"), value="N/A")
            text = _("Click me!")
            if current_song["info"].get("uri"):
                playing_embed.add_field(
                    name=_("Link to the original"),
                    value=f"**[{text}]({current_song['info']['uri']})**",
                )
                if bool(
                    re_search(
                        r"^(?:(?:https?:)?\/\/)?(?:(?:www|m)\.)?(?:(?:youtube\.com|youtu.be))(?:\/(?:[\w\-]+\?v=|embed\/|v\/)?)(?:[\w\-]+)(\S+)?$|",
                        current_song["info"]["uri"],
                    )
                ) and current_song["info"].get(
                    "identifier"
                ):  # YT url check
                    playing_embed.set_thumbnail(
                        url=f"https://img.youtube.com/vi/{current_song['info']['identifier']}/default.jpg"
                    )
            playing_embed.add_field(name=_("Volume"), value=f"{player.volume} %")
            if player.paused:
                playing_embed.add_field(name=_("Playing status"), value=_("`⏸Paused`"))
            if {"title", "length"} <= set(current_song["info"]) and not current_song[
                "info"
            ]["isStream"]:
                button_position = int(
                    100
                    * (player.position / (current_song["info"]["length"] / 1000))
                    / 2.5
                )
                controller = (
                    f"```ɴᴏᴡ ᴘʟᴀʏɪɴɢ: {current_song['info']['title']}\n"
                    f"{(button_position - 1) * '─'}⚪{(40 - button_position) * '─'}\n ◄◄⠀{'▐▐' if not player.paused else '▶'} ⠀►►⠀⠀　　⠀ "
                    f"{str(timedelta(seconds=player.position)).split('.')[0]} / {timedelta(seconds=int(current_song['info']['length'] / 1000))}\n{11*' '}───○ 🔊⠀　　　ᴴᴰ ⚙ ❐ ⊏⊐```"
                )
                playing_embed.description = controller
        else:
            playing_embed.description = _("```No information```")
        if current_song.get("requester_id") and ctx.guild.get_member(
            current_song["requester_id"]
        ):  # check to avoid errors on guild leave
            req_member = ctx.guild.get_member(current_song["requester_id"])
            playing_embed.set_footer(
                text=_("Song requested by: {user}").format(
                    user=req_member.display_name
                ),
                icon_url=req_member.avatar_url_as(format="png", size=64),
            )
        await ctx.send(embed=playing_embed)

    # Event handlers
    async def on_track_end(self, player: pylava.Player):
        await self.bot.redis.execute(
            "LPOP", f"{self.music_prefix}que:{player.guild.id}"
        )  # remove the previous entry
        if not await self.get_queue_length(player.guild.id):
            # That was the last track
            await player.disconnect()
            await self.bot.redis.execute(
                "DEL", f"{self.music_prefix}que:{player.guild.id}"
            )
        else:
            await self.play_entry(
                loads(
                    await self.bot.redis.execute(
                        "LINDEX", f"{self.music_prefix}que:{player.guild.id}", 0
                    )
                ),
                player,
            )

    # Functions
    async def add_entry_to_queue(self, entry: dict, player: pylava.Player):
        """Plays a song or adds to the queue"""
        if not await self.get_queue_length(player.guild.id):
            await self.bot.redis.execute(
                "RPUSH", f"{self.music_prefix}que:{player.guild.id}", dumps(entry)
            )
            await self.play_entry(entry, player)
        else:
            await self.bot.redis.execute(
                "RPUSH", f"{self.music_prefix}que:{player.guild.id}", dumps(entry)
            )
            zws = "@\u200b"
            await self.bot.get_channel(entry.get("channel_id")).send(
                _("🎧 Added {title} to the queue...").format(
                    title=entry.get("info").get("title").replace("@", zws)
                )
            )

    async def play_entry(self, entry: dict, player: pylava.Player):
        zws = "@\u200b"
        await self.bot.get_channel(entry.get("channel_id")).send(
            _("🎧 Playing {title}...").format(
                title=entry.get("info").get("title").replace("@", zws)
            )
        )
        await player.play(entry.get("track"))

    async def get_queue_length(self, guild_id: int) -> Union[int, bool]:
        """Returns the queue's length or False if there is no upcoming songs"""
        query_length = await self.bot.redis.execute(
            "LLEN", f"{self.music_prefix}que:{guild_id}"
        )
        if not query_length or query_length > 0:
            return query_length
        else:
            return False

    async def song_info_builder(self, query: dict) -> discord.Embed:  # TODO
        embed = discord.Embed(title="")
        return embed

    async def initialize_connection(self):
        self.bot.lava = pylava.Connection(self.bot, **self.bot.config.lava_creds)
        await self.bot.lava.connect()
        if not self.bot.lava.connected:
            print(
                f'[Error] Couldn"t connect to the Lavalink server, disabling {self.__class__.__name__}'
            )

            def unload_ext(bot):
                bot.unload_extension(f"cogs.{__name__}")

            await self.bot.loop.run_in_executor(None, partial(unload_ext, self.bot))

    async def cleanup(self):
        for player in self.bot.lava._players.values():
            player.track_callback = None
            await player.stop()
            await player.disconnect()
        queue_keys = await self.bot.redis.execute("KEYS", "{self.music_prefix}que:*")
        if queue_keys:
            await self.bot.redis.execute("DEL", *[key for key in queue_keys])

    def cog_unload(self):
        self.bot.queue.put_nowait(self.cleanup())


def setup(bot):
    bot.add_cog(MusicPlayer(bot))
