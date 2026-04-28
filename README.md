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

```
$ vdocker ps -a

[myapp]
  ID           NAME          IMAGE              COMMAND           CREATED   STATUS
  a1b2c3d4…    myapp-web     nginx:latest       "nginx -g 'da…"  2d ago    Up 2d
  e5f6g7h8…    myapp-api     node:18            "node server.…"  2d ago    Up 2d
  i9j0k1l2…    myapp-db      postgres:15        "postgres"        2d ago    Up 2d

[monitoring]
  ID           NAME               IMAGE                  COMMAND          CREATED   STATUS
  m3n4o5p6…    monitoring-graf…   grafana/grafana:10.2   "/run.sh"        5d ago    Up 5d
  q7r8s9t0…    monitoring-prom…   prom/prometheus:latest  "/bin/prometh…"  5d ago    Up 5d

[standalone]
  ID           NAME          IMAGE         COMMAND            CREATED   STATUS
  u1v2w3x4…    redis-test    redis:7       "redis-server"     1d ago    Up 1d
```

### `vdocker images` — Show images with dependent containers

```
$ vdocker images

nginx:latest (45MB)
└── myapp-web  Up 2d

node:18 (350MB)
└── myapp-api  Up 2d

postgres:15 (380MB)
└── myapp-db  Up 2d

redis:7 (30MB)
└── redis-test  Up 1d
```

Use `--unused` flag to include images with no containers.

### `vdocker volumes` — Show volumes with mounted containers

```
$ vdocker volumes

myapp_db-data (500MB)
└── myapp-db  /var/lib/postgresql/data

myapp_redis-data (10MB)
└── redis-test  /data

unused-volume (0B)
└── (no containers)
```

### `vdocker networks` — Show networks with connected containers

```
$ vdocker networks

myapp_default (bridge)
├── myapp-web   172.18.0.2
├── myapp-api   172.18.0.3
└── myapp-db    172.18.0.4

monitoring_default (bridge)
├── monitoring-grafana      172.19.0.2
└── monitoring-prometheus   172.19.0.3

bridge (bridge)
└── redis-test  172.17.0.2
```

### `vdocker tree` — Full relationship tree

```
$ vdocker tree

Docker Environment
├── [myapp]
│   ├── web (service)
│   │   └── myapp-web  Up 2d
│   │       ├── Image: nginx:latest (45MB)
│   │       ├── Volumes:
│   │       │   └── myapp_static → /usr/share/nginx/html
│   │       └── Networks:
│   │           └── myapp_default (172.18.0.2)
│   ├── api (service)
│   │   └── myapp-api  Up 2d
│   │       ├── Image: node:18 (350MB)
│   │       └── Networks:
│   │           └── myapp_default (172.18.0.3)
│   └── db (service)
│       └── myapp-db  Up 2d
│           ├── Image: postgres:15 (380MB)
│           ├── Volumes:
│           │   └── myapp_db-data → /var/lib/postgresql/data
│           └── Networks:
│               └── myapp_default (172.18.0.4)
├── [standalone]
│   └── redis-test  Up 1d
│       ├── Image: redis:7 (30MB)
│       └── Networks:
│           └── bridge (172.17.0.2)
└── Unused Resources
    ├── Images:
    │   └── alpine:3.18 (7MB)
    └── Volumes:
        └── unused-volume (0B)
```

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
