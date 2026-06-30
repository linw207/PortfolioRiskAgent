# Day11 Feishu Notification

Day11 implements Feishu as the first real notification channel.

## Implemented Scope

- Feishu channel configuration:
  - `POST /notification-channels`
  - `GET /notification-channels`
  - Only `channel_type=feishu` is accepted in Day11.
- Feishu robot webhook sending:
  - `FeishuBotClient`
  - Supports plain webhook and signed webhook secret.
  - Supports `mock://` dry-run webhooks for local tests and smoke scripts.
- Feishu CLI direct message:
  - `channel_type=feishu_cli`
  - Store the recipient `user_open_id` in `webhook_url` or pass it as `user_open_id` when creating the channel.
  - Uses `lark-cli im +messages-send --as user --user-id <open_id> --text ...`.
- Feishu CLI status:
  - `FeishuCLIClient`
  - `GET /notification-channels/feishu-cli/status`
  - `scripts/feishu_cli_status.py`
- Test send:
  - `POST /notification-channels/{channel_id}/test`
- Notification events:
  - `NotificationService.dispatch_event`
  - Used by scheduled task executor for `report_ready`, `task_failed`, `announcement_radar`, and `trade_review_reminder` events.
  - Announcement radar emits `high_risk_event` when high/critical announcement events exist.
- Failure retry:
  - `POST /notification-channels/records/retry-failed`
- Notification records:
  - `GET /notification-channels/records`
  - `POST /notification-channels/records/{record_id}/send`

## Feishu CLI Setup

The CLI guide requires user-assisted browser authorization:

```bash
npm install -g @larksuite/cli
npx -y skills add https://open.feishu.cn --skill -y
lark-cli config init --new
lark-cli auth login --recommend
lark-cli auth status
```

Current local smoke result:

- `lark-cli` is installed at `/opt/homebrew/bin/lark-cli`.
- `lark-cli auth status` is authenticated for user `林炜烨`.
- Direct CLI message sending currently requires extra scope `im:message.send_as_user`.
- Run the following command and complete browser authorization if CLI private-message sending is needed:

```bash
lark-cli auth login --scope "im:message.send_as_user"
```

The PortfolioRiskAgent notification path does not depend on CLI login. Production notifications use Feishu group robot webhook.

## Environment

For real Feishu sending:

```bash
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/...
FEISHU_WEBHOOK_SECRET=optional_secret
```

For local smoke:

```bash
FEISHU_WEBHOOK_URL=mock://day11-feishu
```

For CLI direct message:

```json
{
  "channel_type": "feishu_cli",
  "channel_name": "飞书私聊",
  "user_open_id": "ou_xxx",
  "event_types": ["report_ready", "task_failed", "high_risk_event", "trade_review_reminder"]
}
```

## Verification

Commands run:

```bash
python3 -B -m compileall -q src config log scripts tests
python3 -B -m unittest discover -s tests
python3 -B scripts/day11_feishu_notification_smoke.py
python3 -B scripts/feishu_cli_status.py
```

Smoke result:

- Test message status: sent.
- Event message status: sent.
- Retry failed count: 0.
- Feishu CLI installed: true.
- Feishu CLI authenticated: false.
- Unit tests: 41 passed/covered, with one Mongo integration test skipped when dependencies are unavailable.

## Known Limits

- CLI login requires user browser/keychain participation.
- Real webhook delivery requires a Feishu group robot webhook URL. The repository stores only placeholders.
