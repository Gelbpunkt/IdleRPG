import asyncio
import contextlib
import random

import async_timeout
import Chessnut as chessnut  # muh pep8
import discord

from .bases import Status, TwoPlayerGameCog
from utils.context_managers import temp_message
from utils.formats import escape_markdown


# --------- Image making stuff please ignore ---------

# TODO: Make a microservice for this silly thing
import functools
import io
import itertools
import pathlib
import re
import string
from PIL import Image, ImageDraw, ImageFilter, ImageFont

_CHESS_PIECE_IMAGES = {}
_CHESS_IMAGE_FILE_PATH = pathlib.Path("chess")
for path in _CHESS_IMAGE_FILE_PATH.glob("*.png"):
    _CHESS_PIECE_IMAGES[path.stem] = Image.open(path).convert("RGBA")


def _fen_tokens(fen):
    for c in fen:
        if c == "/":
            continue

        if c.isdigit():
            for i in range(int(c)):
                yield ""
        else:
            yield c


_TEXT_OFFSET = 25
# assume all the pieces are the same width and height
_PIECE_IMAGE_SIZE = next(iter(_CHESS_PIECE_IMAGES.values())).width

try:
    _XY_FONT = ImageFont.truetype("arialbd.ttf", 21)
except Exception:
    _XY_FONT = None

_TEXT_COLOUR = "#9e9e9e"


def _blank_board(width=8, height=8, *, include_xy=True):
    board_image_width = _PIECE_IMAGE_SIZE * width
    board_image_height = _PIECE_IMAGE_SIZE * height

    offset = _TEXT_OFFSET * include_xy
    image_size = (board_image_width + offset, board_image_height + offset)
    image = Image.new("RGBA", image_size, (0,) * 4)

    for y, x in itertools.product(range(height), range(width)):
        tile = "tile_" + "ld"[(x + y) % 2]
        xy = (_PIECE_IMAGE_SIZE * x, _PIECE_IMAGE_SIZE * y)
        image.paste(_CHESS_PIECE_IMAGES[tile], xy)

    if include_xy:
        # 1-8 and A-H text stuff
        text_draw = ImageDraw.Draw(image)
        # 1-8
        for i in range(height, 0, -1):
            char = str(i)
            w, h = text_draw.textsize(char, font=_XY_FONT)
            xy = (
                offset // 4 + board_image_width,
                (height - i) * _PIECE_IMAGE_SIZE + (_PIECE_IMAGE_SIZE - h) // 2,
            )
            text_draw.text(xy, char, fill=_TEXT_COLOUR, font=_XY_FONT)
        # A-H
        for i, char in enumerate(string.ascii_uppercase[:width]):
            w, h = text_draw.textsize(char, font=_XY_FONT)
            xy = (
                i * _PIECE_IMAGE_SIZE + (_PIECE_IMAGE_SIZE - w) // 2,
                board_image_height,
            )
            text_draw.text(xy, char, fill=_TEXT_COLOUR, font=_XY_FONT)
    return image


_BLANK_BOARD = _blank_board()
_GREEN_OVERLAY = Image.new(
    "RGBA", (_PIECE_IMAGE_SIZE, _PIECE_IMAGE_SIZE), (76, 175, 80, 125)
)

# Check circle thingy
def _ellipse(x, y, w, h):
    return (x // 2 - w // 2, y // 2 - h // 2, x // 2 + w // 2, y // 2 + h // 2)


_CHECK_IMAGE = Image.new("RGBA", (_PIECE_IMAGE_SIZE, _PIECE_IMAGE_SIZE), (0, 0, 0, 0))
_CHECK_CIRCLE_D = round(_PIECE_IMAGE_SIZE * 0.85)
_check_image_draw = ImageDraw.Draw(_CHECK_IMAGE)
_bbox = _ellipse(_PIECE_IMAGE_SIZE, _PIECE_IMAGE_SIZE, _CHECK_CIRCLE_D, _CHECK_CIRCLE_D)
_check_image_draw.ellipse(_bbox, (244, 67, 54))
_CHECK_IMAGE = _CHECK_IMAGE.filter(ImageFilter.GaussianBlur(2.5))

del _check_image_draw, _bbox


def _board_image_from_fen(fen, last_move=None, check=None):
    image = _BLANK_BOARD.copy()

    if last_move is not None:

        def overlay(start, end):
            y, x = divmod(chessnut.Game.xy2i(last_move[start:end]), 8)
            xy = (x * _PIECE_IMAGE_SIZE, y * _PIECE_IMAGE_SIZE)
            image.alpha_composite(_GREEN_OVERLAY, xy)

        overlay(None, 2)
        overlay(2, 4)

    for i, char in enumerate(_fen_tokens(fen)):
        y, x = divmod(i, 8)
        if not char:
            continue

        xy = (_PIECE_IMAGE_SIZE * x, _PIECE_IMAGE_SIZE * y)
        colour = "w" if char.isupper() else "b"
        if check == colour and char.lower() == "k":
            image.paste(_CHECK_IMAGE, xy, mask=_CHECK_IMAGE)

        key = colour + char.lower()
        piece = _CHESS_PIECE_IMAGES[key]
        image.paste(piece, xy, mask=piece)

    return image


def _board_file_from_fen(fen, last_move=None, check=None):
    image = _board_image_from_fen(fen, last_move=last_move, check=check)
    file = io.BytesIO()
    image.save(file, "png")

    file.seek(0)
    return discord.File(file, "chess.png")


# -------- End of image making stuff please continue. -------


_SYMBOLS = {"w": "\u26aa", "b": "\u26ab"}
_OTHER_TURNS = {"w": "b", "b": "w"}


_STATUS_MESSAGES = {
    Status.PLAYING: ("Chess", 0x4CAF50),
    Status.QUIT: ("{user} resigned...", 0x9E9E9E),
    Status.TIMEOUT: ("{user} ran out of time...", 0x9E9E9E),
    chessnut.Game.CHECK: ("Check!", 0xFFEB3B),
    chessnut.Game.CHECKMATE: ("Checkmate!", 0xF44336),
    chessnut.Game.STALEMATE: ("Stalemate...", 0x9E9E9E),
}

_COLOUR_RESULTS = {"w": "1-0", "b": "0-1"}


class Clock:
    __slots__ = ("_remaining", "_increment")

    def __init__(self, time=10 * 60, increment=0):
        self._remaining = time
        self._increment = increment

    def __str__(self):
        minutes, seconds = divmod(self._remaining, 60)
        return f"{int(minutes):02d}:{int(seconds):02d}"

    @contextlib.contextmanager
    def wait(self):
        try:
            with async_timeout.timeout(self._remaining) as timeout:
                yield
        finally:
            self._remaining = timeout.remaining + self._increment


class Player:
    __slots__ = ("_user", "_clock")

    def __init__(self, user, clock):
        self._user = user
        self._clock = clock

    def __str__(self):
        return f"`[{self._clock}]` {escape_markdown(str(self._user))}"

    def wait_for_move(self):
        return self._clock.wait()

    @property
    def user(self):
        return self._user


# XXX: Assumes normal chess. Variations like Chess 960 would break this.
_CASTLE_MOVES = {
    ("0-0", "w"): "e1g1",
    ("0-0", "b"): "e8g8",
    ("0-0-0", "w"): "e1c1",
    ("0-0-0", "b"): "e1c8",
}


def _translate_castle(game, move):
    return _CASTLE_MOVES.get((move, game.state.player), "")


_SAN_REGEX = re.compile(r"([NBRQK])?([a-h]?[1-8]?)(x)?([a-h][1-8])=?([QBNR])?[\#\+]?$")


def _translate_san(game, move):
    match = _SAN_REGEX.match(move)
    if not match:
        return ""

    piece, from_hint, takes, end, promotion = match.groups("")
    if len(from_hint) == 2:
        return from_hint + end

    piece_at_end = game.board.get_piece(game.xy2i(end))
    if piece_at_end.isspace() and takes:
        # Nonsensical san, there is no piece to take.
        return ""
    elif takes and not (piece or from_hint):
        # Pawn capture requires a file.
        return ""

    piece = piece or "P"
    if game.state.player == "b":
        piece = piece.lower()

    squares = [i for i, p in enumerate(game.board._position) if p == piece]
    if not squares:
        return ""

    if len(squares) == 1:
        return game.i2xy(squares[0]) + end + promotion.lower()

    if piece not in chessnut.moves.MOVES:
        return ""

    rays = chessnut.moves.MOVES[piece]

    final_result = ""
    for start in squares:
        if from_hint not in game.i2xy(start):
            continue

        for ray in rays[start]:
            result = next(
                (
                    move
                    for move in game._trace_ray(start, piece, ray, game.state.player)
                    if move[2:4] == end
                    and (not promotion or promotion.lower() == move[-1])
                ),
                "",
            )
            if result:
                if final_result and not from_hint:
                    # Ambiguous san, this is not allowed.
                    return ""
                else:
                    final_result = result

    return final_result


_UCI_REGEX = re.compile(r"([a-h][1-8])[ -]?([a-h][1-8])[ -]?([qrbn])?$", re.IGNORECASE)


def _translate_uci(game, move):
    match = _UCI_REGEX.fullmatch(move)
    if not match:
        return ""

    return "".join(match.groups("")).lower()


def _translate(game, move):
    return (
        _translate_castle(game, move)
        or _translate_san(game, move)
        or _translate_uci(game, move)
    )


def _safe_sample(population, k):
    # random.sample complains if the number of items is less than k.
    # We don't care about that really.
    return random.sample(population, min(k, len(population)))


class ChessSession:
    def __init__(self, ctx, opponent):
        self._game = chessnut.Game()
        self._players = {
            t: Player(user, Clock())
            for t, user in zip("wb", random.sample((ctx.author, opponent), 2))
        }

        self._status = Status.PLAYING
        self.ctx = ctx

        self._game_screen = (
            discord.Embed(colour=0x00FF00)
            .set_author(name=f"Chess")
            .set_image(url="attachment://chess.png")
        )
        self._last_move = None
        self._image = None

    def _in_check(self):
        return self._game.status in [self._game.CHECK, self._game.CHECKMATE]

    def _push_move(self, move):
        self._game.apply_move(move)
        self._last_move = move

    def _check(self, m):
        current = self.current.user
        if not (m.channel == self.ctx.channel and m.author == current):
            return

        if m.content.lower() in {"quit", "stop"}:
            self._status = Status.QUIT
            return True

        translated = _translate(self._game, m.content)
        if not translated:
            return

        try:
            self._push_move(translated)
        except Exception:
            return

        return True

    async def _make_move(self):
        try:
            with self.current.wait_for_move():
                await self.ctx.bot.wait_for("message", check=self._check)
        except asyncio.TimeoutError:
            self._status = Status.TIMEOUT

    def _instructions(self):
        if self._game.state.turn > 1:
            return ""

        sample = _safe_sample(self._game.get_moves(), 5)
        joined = ", ".join(f"`{c}`" for c in sample)
        return (
            "**Instructions:**\n"
            "Type the position of the piece you want to move,\n"
            "and where you want to move it.\n"
            f"**Example:**\n{joined}"
        )

    async def _update_display(self):
        game = self._game
        turn = game.state.player
        screen = self._game_screen
        player = self.current

        check = turn if self._in_check() else None
        run = self.ctx.bot.loop.run_in_executor
        get_file = functools.partial(
            _board_file_from_fen, str(game.board), self._last_move, check
        )
        self._image = await run(None, get_file)

        # thank god dicts are ordered...
        formats = {
            turn: f"{_SYMBOLS[turn]} = {player}"
            for turn, player in self._players.items()
        }

        status = self.status
        is_playing = self._status is Status.PLAYING

        icon = discord.Embed.Empty
        if is_playing:
            formats[turn] = f"**{formats[turn]}**"
            icon = player.user.avatar_url
            if check:
                # We're in check, not checkmate, otherwise this would be END
                status = self._game.CHECK
        elif self._status is Status.TIMEOUT:
            name = formats[turn].partition(" = ")[-1]
            formats[turn] = f"\U0001f534 = {name}"

        screen.description = "\n".join(formats.values())
        if is_playing:
            screen.description += "\n\n" + self._instructions()

        header, colour = _STATUS_MESSAGES[status]
        screen.colour = colour
        screen.set_author(name=header.format(user=player.user), icon_url=icon)

    async def _loop(self):
        while True:
            await self._update_display()

            async with temp_message(
                self.ctx, file=self._image, embed=self._game_screen
            ):
                await self._make_move()

            if self._status is not Status.PLAYING:
                break

            status = self._game.status
            if status not in [self._game.NORMAL, self._game.CHECK]:
                self._status = Status.END
                break

    async def run(self):
        try:
            return await self._loop()
        finally:
            await self._update_display()
            self._game_screen.set_footer(text=self.result())
            await self.ctx.send(file=self._image, embed=self._game_screen)

    def result(self):
        status = self.status

        if status in [self._game.CHECKMATE, Status.QUIT, Status.TIMEOUT]:
            return _COLOUR_RESULTS[_OTHER_TURNS[self._game.state.player]]

        if status in [self._game.STALEMATE]:
            return "\xbd - \xbd"

        return "?"

    @property
    def current(self):
        return self._players[self._game.state.player]

    @property
    def other(self):
        return self._players[_OTHER_TURNS[self._game.state.player]]

    @property
    def status(self):
        if self._status is not Status.END:
            return self._status

        return self._game.status


class Chess(TwoPlayerGameCog, game_cls=ChessSession):
    async def _end_game(self, ctx, inst, result):
        return


def setup(bot):
    bot.add_cog(Chess(bot))


def teardown(bot):
    _BLANK_BOARD.close()
    _GREEN_OVERLAY.close()
    _CHECK_IMAGE.close()

    # Close all images in the piece dict
    while _CHESS_PIECE_IMAGES:
        _CHESS_PIECE_IMAGES.popitem()[1].close()
