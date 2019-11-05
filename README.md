# IdleRPG

[![Build Status](https://api.travis-ci.com/Gelbpunkt/IdleRPG.svg)](https://travis-ci.com/Gelbpunkt/IdleRPG)
[![Dockerhub](https://img.shields.io/badge/Pull%20IdleRPG-from%20Dockerhub-orange)](https://hub.docker.com/r/gelbpunkt/idlerpg)
[![okapi](https://img.shields.io/badge/Pull%20okapi-from%20Dockerhub-black)](https://hub.docker.com/r/gelbpunkt/okapi)
[![teatro](https://img.shields.io/badge/Pull%20teatro-from%20Dockerhub-green)](https://hub.docker.com/r/gelbpunkt/teatro)

This is the code for the IdleRPG Discord Bot.

You may [submit an issue](https://git.travitia.xyz/Adrian/IdleRPG/issues) or [open a pull request](https://git.travitia.xyz/Adrian/IdleRPG/merge_requests) at any time.

## License

The IdleRPG Project is licensed under the terms of the [GNU Affero General Public License 3.0](https://git.travitia.xyz/Adrian/IdleRPG/blob/v4/LICENSE) ("AGPL"). It is a GPLv3 with extra clause for use over networks (see section 13).

[AGPL for humans](<https://tldrlegal.com/license/gnu-affero-general-public-license-v3-(agpl-3.0)>).

## Current goals

Please see [#32](https://git.travitia.xyz/Adrian/IdleRPG/issues/32)

## Running it

Note: This requires you to have Podman and Git working.

```sh
git clone https://git.travitia.xyz/Adrian/IdleRPG.git
cd IdleRPG
./scripts/setup.sh
systemctl start "podman-*"
```

For a quick and ugly deploy, you might want to try `./scripts/beta.sh`. It is for a non-persistent storage.

## Utility

IdleRPG uses [black](https://github.com/ambv/black), [flake8](https://github.com/PyCQA/flake8) and [isort](https://github.com/timothycrosley/isort) for code style. Please always run `./scripts/format.sh` before submitting a pull request and fix any problems.

`./scripts/dumpdb.sh db_name` will update the database scheme from the postgres container.
