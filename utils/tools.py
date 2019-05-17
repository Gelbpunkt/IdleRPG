"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt
This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""
from datetime import timedelta


def todelta(time):
    value = float(time[:-1])
    dtype = time[-1]
    if dtype == "d":
        return timedelta(days=value)
    if dtype == "h":
        return timedelta(hours=value)
    if dtype == "m":
        return timedelta(minutes=value)
    if dtype == "s":
        return timedelta(seconds=value)
