# 桥面伸缩缝复测送检

桥面养护巡查组长使用此工程。校正温差造成的伸缩缝读数变化，用稳健斜率筛出持续偏移的构件，再核对车道占用安排复测。

## 启动

从项目目录运行 `docker compose up --build -d`。服务端口为 `18828`。
打开 `http://127.0.0.1:18828/` 查看桥面伸缩缝复测送检工作台。

```sh
curl -s http://127.0.0.1:18828/healthz
curl -s http://127.0.0.1:18828/api/summary
docker compose exec -T app python -m jointfolio.cli plan --summary
docker compose exec -T app python -m jointfolio.cli inspect replay
docker compose exec -T app pytest -q
```

从 `/api/plan` 读取逐单方案及 `run_id`。试算适用于替换数据或调整资源额度。
用 `POST /api/releases` 登记时一并传当次 `run_id`、快照日、额度和当前登记版本，首次填 `expected_generation=0`。
`GET /api/releases` 返回登记历史，`GET /api/releases/1` 可回读同一版完整证据。登记数据库默认放在 Compose 卷内。

[业务和字段](docs/SPEC.md) · [模块与回归用例](docs/DEPTH.md) · [接口操作](docs/API.md) · [判定和复核规则](docs/OPERATIONS.md)

数据由行业情景构造，用于回放。停服务运行 `docker compose down`。
