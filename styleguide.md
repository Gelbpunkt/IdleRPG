## Styleguide

Please keep to these conventions when contributing to IdleRPG.

### License Header

At every file's top, insert the license header please. You may fine it in most of the files, just copy paste it.

### Black, flake8 and isort

We use black for codestyle and isort for import ordering.
Always run `test.sh` and run `pip3 install black && pip3 install flake8 && pip3 install isort` before. Fix any issues caused.

### Import Order

Order your imports with `isort -rc .`.
Also, **no empty lines after license header**.
2 empty lines after the imports.


Example:

```py
"""
License blah blah
"""
import asyncio
import functools
import random

import discord
from discord.ext import commands

from cogs.classes import genstats
from cogs.shard_communication import user_on_cooldown as user_cooldown
from utils import misc as rpgtools
from utils.checks import has_char
from utils.tools import todelta


class Whatever():
```
