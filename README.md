# vdocker

A CLI tool that visualizes Docker objects (containers, images, volumes, networks) and their relationships in grouped/tree format.

Solves the problem of containers from different services being mixed together in `docker ps` output.

## Installation

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

## Requirements

- Docker running
- Python 3.10+ (for pip install)

## License

MIT

## Author

Hyunwoo Song <justperson94@gmail.com>
