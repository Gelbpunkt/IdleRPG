import re

from discord.utils import escape_markdown as discord_escape_markdown


def get_backticks(text):
    top = 0
    matches = re.finditer(r"(`)+", text, re.MULTILINE)
    for match in matches:
        if (g := len(match.group())) > top:
            top = g
    return top


def codeline(text: str, num: int = None):
    if not num:
        num = get_backticks(text) + 1
    return f"{num*'`'}{text}{num*'`'}"


def escape_markdown(text):
    text = discord_escape_markdown(text, as_needed=False).replace("\\", "\u200b")
    return codeline(text, 2)
