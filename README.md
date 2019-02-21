# IdleRPG

This is the code for the IdleRPG Discord Bot.

You may [submit an issue](https://github.com/Gelbpunkt/IdleRPG/issues) or open pull requests at any time.

The master branch is always the *latest stable* version. For development versions, check other branches please.

It is currently published as "All rights reserved", but we are working on a better licensing to give users more freedoms.

## Current goals

1. Work on a total rewrite for v3.4
2. Add all features from Travitia in v5
3. Multiproces

Todo in v3.4:

- Subclass context and .send to allow escaping mass-mentions by default
- Re-use the data from checks as ctx attributes
- Cleanup, remove unnecessary code, beautify
- Use custom converters instead of own handling every time
- Move battles to a backend function
- Clean up the directory structure
- Move pagination to a module

## Can I selfhost?

The answer is simple: **No** (where is the fun at hosting a big MMO your own? Cool, you got everything, but where is the fun of the global community?)

You're allowed to selfhost for testing your own changes that you will submit with a pull request later.

## How do I test my changes?

Note: This requires you to have Redis and Postgres working, and, depending on what you are doing, Lavalink.

```
git clone https://github.com/Gelbpunkt/IdleRPG
cd IdleRPG
pip3 install -r requirements.txt
mv config.py.example config.py
(edit config.py to your needs now)
(now do your changes)
python3 idlerpg.py
```

A systemd unit file has been bundled as `idlerpg.service`.

## Code style

IdleRPG uses [black](https://github.com/ambv/black) for code style. Please always run `test.sh` before submitting a pull request.

Make sure black is done and flake8 throws no issues, then you are ready to submit a PR.
