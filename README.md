# IdleRPG

This is the code for the IdleRPG Discord Bot.

You may [submit an issue](https://github.com/Gelbpunkt/IdleRPG/issues) or open pull requests at any time.

## License

The IdleRPG Project is licensed under the terms of the [GNU Affero General Public License 3.0](https://github.com/Gelbpunkt/IdleRPG/blob/v3.6/LICENSE.md) ("AGPL").

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

1. Prettify v3.6 and add anti-selfbot system (v3.6 branch)

## Can I selfhost?

[Yes, as long as you provide the code for everyone. See section 13 of this link.](https://www.gnu.org/licenses/agpl-3.0.en.html)

## How do I test my changes?

Note: This requires you to have Redis and Postgres working, and, depending on what you are doing, Lavalink.

```
git clone https://github.com/Gelbpunkt/IdleRPG
cd IdleRPG
(edit config.py.example to your database credentials)
./setup.sh
(do changes now)
systemctl start idlerpg
```

A systemd unit file has been bundled as `idlerpg.service`.

## Contributing

IdleRPG uses [black](https://github.com/ambv/black) for code style. Please always run `test.sh` before submitting a pull request.

Make sure black is done and flake8 throws no issues, then you are ready to submit a PR.

**Make sure you sign the CLA [here](https://cla-assistant.io/Gelbpunkt/IdleRPG), else we cannot merge your changes.**
