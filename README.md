# vdocker

Docker 오브젝트(컨테이너, 이미지, 볼륨, 네트워크) 간의 관계를 그룹화/트리 형태로 시각화하는 CLI 도구.

`docker ps`에서 같은 서비스의 컨테이너가 뒤섞여 보이는 문제를 해결합니다.

## 설치

### 바이너리 (Python 불필요)

[Releases](https://github.com/justperson94/vdocker/releases) 에서 바이너리를 다운로드:

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

### 소스에서 설치

```bash
git clone https://github.com/justperson94/vdocker.git
cd vdocker
pip install -e .
```

## 사용법

### `vdocker ps` — 컨테이너를 compose 프로젝트별로 그룹화

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

### `vdocker images` — 이미지별 종속 컨테이너

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

미사용 이미지까지 보려면 `--unused` 플래그를 사용합니다.

### `vdocker volumes` — 볼륨별 마운트된 컨테이너

```
$ vdocker volumes

myapp_db-data (500MB)
└── myapp-db  /var/lib/postgresql/data

myapp_redis-data (10MB)
└── redis-test  /data

unused-volume (0B)
└── (no containers)
```

### `vdocker networks` — 네트워크별 연결된 컨테이너

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

### `vdocker tree` — 전체 관계 트리

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

## 공통 옵션

| 옵션 | 설명 |
|------|------|
| `-a, --all` | 중지된 컨테이너 포함 |
| `--json` | JSON 형식으로 출력 |
| `--unused` | 미사용 이미지 표시 (`images` 전용) |

## 요구사항

- Docker 실행 중
- pip 설치 시: Python 3.10+

## 라이선스

MIT

## 작성자

Hyunwoo Song <justperson94@gmail.com>
