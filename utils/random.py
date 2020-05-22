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
import secrets

from collections.abc import Sequence, Set

choice = secrets.choice
randbits = secrets.randbits


def sample(population, k):
    """Chooses k unique random elements from a population sequence or set."""
    if isinstance(population, Set):
        population = tuple(population)
    if not isinstance(population, Sequence):
        raise TypeError(
            "Population must be a sequence or set.  For dicts, use list(d)."
        )

    n = len(population)
    if not 0 <= k <= n:
        raise ValueError("Sample larger than population or is negative")

    results = []
    for i in range(k):
        results.append(population[secrets.randbelow(n - i)])

    return results


def shuffle(population):
    """Returns a shuffled list"""
    return sample(population, len(population))


def randint(a, b):
    """Return random integer in range [a, b], including both end points."""
    return secrets.randbelow(b - a + 1) + a
