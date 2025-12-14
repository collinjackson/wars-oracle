## AWBW turn relay (Cloud Run + Firestore)

Location: `turn-relay/`

What it does
- Maintains a websocket to `wss://awbw.amarriner.com/node/game/{gameId}`.
- Dedupes `NextTurn` events, posts concise updates to a Discord webhook.
- Optionally stores each observed turn in Firestore (one fetch per turn; no GCS needed).
- Exposes HTTP endpoints for health and turn reads (MCP-friendly).

Env vars
- Required: `GAME_ID`, `DISCORD_WEBHOOK_URL`
- Optional: `AWBW_WS_URL`, `FIRESTORE_PROJECT_ID` (or `GCLOUD_PROJECT`), `FIRESTORE_COLLECTION` (default `awbw_turns`), `RECONNECT_SECONDS`, `MAX_SOCKET_MINUTES` (default 55), `REPLAY_FETCH_URL_TEMPLATE` (single GET per turn).

Run locally (Node 18+)
- `npm install`
- `npm run dev` (or `npm run build && npm start`)

HTTP endpoints (on `$PORT`, default 8080)
- `/health`
- `/turn/status` or `/turn/latest` (uses env `GAME_ID` if query `gameId` omitted)
- `/turn/get?gameId=...&turnKey=...`
- `/turn/range?gameId=...&limit=20`

Docker
- `docker build -t awbw-relay .`
- `docker run -e GAME_ID=... -e DISCORD_WEBHOOK_URL=... -p 8080:8080 awbw-relay`

Cloud Run deploy (example)
```
gcloud run deploy awbw-relay \
  --image gcr.io/PROJECT/awbw-relay \
  --region=REGION \
  --min-instances=1 \
  --set-env-vars GAME_ID=...,DISCORD_WEBHOOK_URL=...,FIRESTORE_PROJECT_ID=...
```

