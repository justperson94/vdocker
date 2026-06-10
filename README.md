# vdocker

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](https://github.com/justperson94/vdocker/blob/main/LICENSE)
[![GitHub release](https://img.shields.io/github/v/release/justperson94/vdocker?style=for-the-badge&color=2496ED)](https://github.com/justperson94/vdocker/releases)
[![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20macOS-lightgrey?style=for-the-badge)](https://github.com/justperson94/vdocker/releases)

A CLI tool that visualizes Docker objects (containers, images, volumes, networks) and their relationships in grouped/tree format.

Solves the problem of containers from different services being mixed together in `docker ps` output.

## Installation

### Homebrew (macOS / Linux)

```bash
brew install justperson94/tap/vdocker
```

### Binary (no Python required)

Download from [Releases](https://github.com/justperson94/vdocker/releases):

```bash
# Linux
curl -L -o vdocker https://github.com/justperson94/vdocker/releases/latest/download/vdocker-linux-amd64
chmod +x vdocker
sudo mv vdocker /usr/local/bin/
```

### pip

```bash
pip install git+https://github.com/justperson94/vdocker.git
```

### From source

```bash
git clone https://github.com/justperson94/vdocker.git
cd vdocker
pip install -e .
```

## Usage

### `vdocker ps` — Group containers by compose project

![vdocker ps](docs/ps.svg)

### `vdocker images` — Show images with dependent containers

![vdocker images](docs/images.svg)

Use `--unused` flag to include images with no containers.

### `vdocker volumes` — Show volumes with mounted containers

![vdocker volumes](docs/volumes.svg)

### `vdocker networks` — Show networks with connected containers

![vdocker networks](docs/networks.svg)

### `vdocker tree` — Full relationship tree

![vdocker tree](docs/tree.svg)

## Options

| Option | Description |
|--------|-------------|
| `-a, --all` | Include stopped containers |
| `--json` | Output as JSON |
| `--unused` | Show unused images (`images` only) |

## Notes

- The working directory path shown next to project names (e.g. `[myapp]  /home/user/projects/myapp`) is only available for containers started via `docker compose up`. Standalone containers (`docker run`) do not have this information.

## Requirements

- Docker running
- Python 3.10+ (for pip install)

## License

MIT

## Author

Hyunwoo Song <justperson94@gmail.com>
