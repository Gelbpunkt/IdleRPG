## Styleguide

Please keep to these conventions when contributing to IdleRPG.

### License Header

At every file's top, insert the license header please. You may fine it in most of the files, just copy paste it.

### Black

Always run `test.sh` and run `pip3 install black && pip3 install flake8` before. Fix any issues caused.

### Import Order

Order your imports alphabetically. Partial imports after normal ones, seperated with one line.
Also, **no empty lines after license header and imports**.
2 empty lines after last imports.


Example:

```py
"""
License blah blah
"""
import aiohttp
import aioredis
import asyncio
import asyncpg
import config
import discord
import datetime
import os
import traceback

from classes.context import Context
from discord.ext import commands
from utils import paginator


class Whatever():
```
