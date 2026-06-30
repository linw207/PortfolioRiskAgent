# 实时行情接入说明

## 当前问题

早期 Day4 行情链路以 AKShare 和本地样例数据为主，适合跑通 Agent 闭环，但存在两个边界：

- AKShare spot 接口更适合 A 股批量快照，不适合作为统一实时行情源。
- 港股实时行情未接入专业 provider，只能依赖样例降级。

## 新增设计

当前行情网关按如下顺序取数：

```text
MARKET_DATA_PROVIDER_ORDER=itick,akshare,sample
```

含义：

- `itick`：优先用于港股 `.HK` 的实时 tick。
- `akshare`：用于 A 股 `.SH/.SZ` 行情快照。
- `sample`：所有外部源不可用时降级，保证演示和测试不断链。

## 配置

```env
MARKET_DATA_PROVIDER_ORDER=itick,akshare,sample
ITICK_API_TOKEN=
ITICK_BASE_URL=https://api.itick.org
ITICK_TIMEOUT_SECONDS=5
REALTIME_QUOTE_CACHE_TTL_SECONDS=3
```

拿到 iTick token 后，把 token 写入 `.env`：

```env
ITICK_API_TOKEN=your_token_here
```

然后重启服务。

## 支持的代码格式

```text
600519       -> 600519.SH
000001       -> 000001.SZ
300750.SZ    -> 300750.SZ
700          -> 00700.HK
700.HK       -> 00700.HK
00700.HK     -> 00700.HK
```

## 验证

查看健康状态：

```bash
curl http://127.0.0.1:8000/health
```

调用工具：

```bash
curl -X POST http://127.0.0.1:8000/tools/get_stock_price/call \
  -H 'Content-Type: application/json' \
  -d '{"arguments":{"symbol":"00700.HK"}}'
```

无 `ITICK_API_TOKEN` 时，港股会降级到 `local_sample`，返回 `degraded=true`。配置 token 后，港股优先走 `iTick`，返回 `source=iTick`、`realtime=true`。

## 边界

- 当前接入的是 iTick REST tick，不包含 WebSocket 实时订阅服务。
- WebSocket 适合后续做行情看板实时刷新，但需要单独的连接管理、心跳、重连和消息广播层。
- A 股仍保留 AKShare 优先，后续可接入 Tushare、iTick A 股或其他实时 provider。

