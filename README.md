# IdleRPG

This is the code for the IdleRPG Discord Bot.

You may [submit an issue](https://github.com/Gelbpunkt/IdleRPG/issues) or open pull requests at any time.

The master branch is always the *latest stable* version. For development versions, check other branches please.

## License

The IdleRPG Project is dual-licensed under the terms of the [GNU Affero General Public License 3.0](https://github.com/Gelbpunkt/IdleRPG/blob/v3.4-dev/LICENSE.md) ("AGPL") for non-commercial and the Travitia License for commercial use. A copy of the AGPL can be found in the [LICENSE.md](https://github.com/Gelbpunkt/IdleRPG/blob/v3.4-dev/LICENSE.md) file. The Travitia license can be obtained by sending a formal request to business [at] travitia \<dot\> xyz with usecase, name and address.

The AGPL allows you to:
- [x] Modify the code
- [x] Distribute it

It however does not allow you to:
- [ ] Sublicense
- [ ] Hold liable

You must:
- Include the copyright
- Include the License
- Disclose the source
- State changes

Summary and information taken from [here](https://tldrlegal.com/license/gnu-affero-general-public-license-v3-(agpl-3.0)).

## Current goals

1. Work on a total rewrite for v3.4
2. Add all features from Travitia in v5
3. Multiprocess

Todo in v3.4:

- Subclass context and .send to allow escaping mass-mentions by default
- Re-use the data from checks as ctx attributes
- Cleanup, remove unnecessary code, beautify
- Use custom converters instead of own handling every time
- Move battles to a backend function
- Move pagination to a module

## Can I selfhost?

[Yes, as long as you provide the code for everyone.](https://github.com/Gelbpunkt/IdleRPG/blob/vhttps://github.com/Gelbpunkt/IdleRPG/blob/v3.4-dev/LICENSE.md#13-remote-network-interaction-use-with-the-gnu-general-public-license)

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
