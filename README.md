# IdleRPG

[![Build Status](https://api.travis-ci.com/Gelbpunkt/IdleRPG.svg)](https://travis-ci.com/Gelbpunkt/IdleRPG)

This is the code for the IdleRPG Discord Bot.

You may [submit an issue](https://github.com/Gelbpunkt/IdleRPG/issues) or [open a pull request](https://github.com/Gelbpunkt/IdleRPG/pulls) at any time.

## License

The IdleRPG Project is licensed under the terms of the [GNU Affero General Public License 3.0](https://github.com/Gelbpunkt/IdleRPG/blob/v4/LICENSE) ("AGPL").

[AGPL for humans](<https://tldrlegal.com/license/gnu-affero-general-public-license-v3-(agpl-3.0)>).

## Current goals

Please see [#32](https://github.com/Gelbpunkt/IdleRPG/issues/32)

## Can I selfhost?

[Yes, as long as you provide the code for everyone. See section 13 of this link.](https://www.gnu.org/licenses/agpl-3.0.en.html)

## How do I test my changes?

Note: This requires you to have Podman and Git working.

```sh
git clone https://github.com/Gelbpunkt/IdleRPG
cd IdleRPG
./scripts/setup.sh
systemctl start "podman-*"
```

## Contributing

IdleRPG uses [black](https://github.com/ambv/black), [flake8](https://github.com/PyCQA/flake8) and [isort](https://github.com/timothycrosley/isort) for code style. Please always run `./scripts/format.sh` before submitting a pull request and fix any problems.

**Make sure you sign the CLA [here](https://cla-assistant.io/Gelbpunkt/IdleRPG), else we cannot merge your changes.**
