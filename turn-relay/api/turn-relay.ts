import http from "node:http";
import { URL } from "node:url";

/**
 * AWBW -> Discord turn relay with optional Firestore turn storage.
 * - Opens a websocket to `wss://awbw.amarriner.com/node/game/{gameId}`
 * - Listens for `NextTurn` messages
 * - Posts a short notification to a Discord webhook
 * - Optionally stores the observed turn in Firestore (no blob store needed)
 *
 * Intended to run as a long-lived worker (Node 18+/serverless background/Cloud Run/Fly).
 * Vercel/Firebase request-scoped functions are not suitable for maintaining the socket.
 * Socket lifetime is bounded via MAX_SOCKET_MINUTES to force periodic reconnects.
 * Includes a lightweight HTTP server for health + MCP-ish reads backed by Firestore.
 */

type NextTurnEnvelope = {
  NextTurn: {
    action: string;
    day: number;
    nextFunds: number;
    nextPId: number;
    nextTimer: number;
    nextTurnStart: string;
    nextWeather: string;
    repaired: Array<{ units_hit_points: number; units_id: string }>;
    supplied: unknown[];
  };
};

type WebSocketCtor = typeof WebSocket;

const gameId = process.env.GAME_ID;
const discordWebhook = process.env.DISCORD_WEBHOOK_URL;
const baseUrl =
  process.env.AWBW_WS_URL ||
  (gameId ? `wss://awbw.amarriner.com/node/game/${gameId}` : undefined);
const reconnectSeconds = Number(process.env.RECONNECT_SECONDS || "5");
const maxSocketMinutes = Number(process.env.MAX_SOCKET_MINUTES || "55");
const firestoreProjectId =
  process.env.FIRESTORE_PROJECT_ID || process.env.GCLOUD_PROJECT;
const firestoreCollection =
  process.env.FIRESTORE_COLLECTION || "awbw_turns";
const replayFetchTemplate = process.env.REPLAY_FETCH_URL_TEMPLATE;
const port = Number(process.env.PORT || "8080");

if (!gameId || !discordWebhook || !baseUrl) {
  console.error(
    "[turn-relay] Missing env: GAME_ID, DISCORD_WEBHOOK_URL, or AWBW_WS_URL"
  );
  process.exit(1);
}

let lastTurnKey: string | undefined;
let firestore: any;

async function resolveWebSocket(): Promise<WebSocketCtor> {
  if (typeof WebSocket !== "undefined") return WebSocket;
  const mod = await import("ws");
  return (mod.default || mod.WebSocket) as WebSocketCtor;
}

async function resolveFirestore() {
  if (firestore || !firestoreProjectId) return firestore;
  const mod = await import("@google-cloud/firestore").catch((err) => {
    console.warn("[turn-relay] Firestore unavailable", err);
    return null;
  });
  if (!mod) return undefined;
  const { Firestore } = mod as any;
  firestore = new Firestore({ projectId: firestoreProjectId });
  return firestore;
}

async function postToDiscord(payload: NextTurnEnvelope["NextTurn"]) {
  const summary = [
    `Day ${payload.day}`,
    `pid ${payload.nextPId}`,
    `funds ${payload.nextFunds}`,
    `starts ${payload.nextTurnStart}`,
    `timer ${(payload.nextTimer / 1000).toFixed(0)}s`,
    `weather ${payload.nextWeather}`,
  ].join(" • ");

  const body = {
    content: `AWBW turn update: ${summary}`,
  };

  const res = await fetch(discordWebhook!, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Webhook post failed ${res.status}: ${text}`);
  }
}

async function fetchReplayIfConfigured(turnKey: string) {
  if (!replayFetchTemplate) return undefined;
  const url = replayFetchTemplate
    .replace("{gameId}", String(gameId))
    .replace("{turnKey}", turnKey);
  const res = await fetch(url, { method: "GET" });
  if (!res.ok) {
    throw new Error(`Replay fetch failed ${res.status}: ${await res.text()}`);
  }
  return res.json();
}

async function storeTurn(
  turnKey: string,
  payload: NextTurnEnvelope["NextTurn"]
) {
  const db = await resolveFirestore();
  if (!db) return;
  const docId = `${gameId}-${turnKey}`;
  const docRef = db.collection(firestoreCollection).doc(docId);
  const doc = await docRef.get();
  if (doc.exists) return;

  let replay: any = undefined;
  try {
    replay = await fetchReplayIfConfigured(turnKey);
  } catch (err) {
    console.warn("[turn-relay] replay fetch skipped/failed", err);
  }

  const record = {
    gameId,
    turnKey,
    observedAt: new Date().toISOString(),
    nextTurn: payload,
    replay: replay ?? null,
  };
  await docRef.set(record);
}

async function startRelay(backoffMs = 0): Promise<void> {
  const WebSocketImpl = await resolveWebSocket();

  if (backoffMs > 0) {
    await new Promise((r) => setTimeout(r, backoffMs));
  }

  console.log(`[turn-relay] connecting to ${baseUrl}`);
  const socket = new WebSocketImpl(baseUrl!);

  let isClosed = false;
  const lifetimeTimeout =
    maxSocketMinutes > 0
      ? setTimeout(() => {
          console.warn("[turn-relay] max socket age reached, closing");
          socket.close();
        }, maxSocketMinutes * 60 * 1000)
      : undefined;

  const scheduleReconnect = (reason: string) => {
    if (isClosed) return;
    isClosed = true;
    if (lifetimeTimeout) clearTimeout(lifetimeTimeout);
    const nextDelay = Math.min(
      backoffMs ? backoffMs * 2 : reconnectSeconds * 1000,
      30_000
    );
    console.warn(`[turn-relay] reconnecting in ${nextDelay}ms (${reason})`);
    startRelay(nextDelay).catch((err) =>
      console.error("[turn-relay] reconnect failed", err)
    );
  };

  socket.onopen = () => {
    console.log("[turn-relay] websocket open");
  };

  socket.onmessage = async (event) => {
    try {
      const data =
        typeof event.data === "string" ? event.data : event.data.toString();
      const parsed = JSON.parse(data) as NextTurnEnvelope;
      if (!parsed?.NextTurn) return;

      const { NextTurn } = parsed;
      const turnKey = `${NextTurn.nextTurnStart}-${NextTurn.nextPId}`;

      if (turnKey === lastTurnKey) {
        return;
      }

      await storeTurn(turnKey, NextTurn);
      await postToDiscord(NextTurn);
      lastTurnKey = turnKey;
      console.log(
        `[turn-relay] notified turn ${NextTurn.nextTurnStart} pid ${NextTurn.nextPId}`
      );
    } catch (err) {
      console.error("[turn-relay] onmessage error", err);
    }
  };

  socket.onerror = (event) => {
    console.error("[turn-relay] websocket error", event);
  };

  socket.onclose = (event) => {
    console.warn(
      `[turn-relay] websocket closed code=${event.code} reason=${event.reason}`
    );
    scheduleReconnect("close");
  };

  // ws library emits ping/pong; browser WS does not expose ping.
  // If the runtime supports it, reply to ping to keep the connection alive.
  if ("onping" in socket) {
    (socket as any).onping = () => {
      if (typeof (socket as any).pong === "function") {
        (socket as any).pong();
      }
    };
  }
}

type ApiResponse =
  | { ok: true; data: any }
  | { ok: false; error: string; status?: number };

function sendJson(res: http.ServerResponse, status: number, body: ApiResponse) {
  const payload = JSON.stringify(body);
  res.writeHead(status, {
    "Content-Type": "application/json",
    "Content-Length": Buffer.byteLength(payload),
  });
  res.end(payload);
}

async function requireFirestore(res: http.ServerResponse) {
  const db = await resolveFirestore();
  if (!db) {
    sendJson(res, 503, { ok: false, error: "firestore not configured" });
    return null;
  }
  return db;
}

async function handleTurnLatest(
  url: URL,
  res: http.ServerResponse
): Promise<void> {
  const db = await requireFirestore(res);
  if (!db) return;
  const game = url.searchParams.get("gameId") || gameId;
  if (!game) {
    sendJson(res, 400, { ok: false, error: "gameId required" });
    return;
  }
  const snapshot = await db
    .collection(firestoreCollection)
    .where("gameId", "==", game)
    .orderBy("observedAt", "desc")
    .limit(1)
    .get();
  if (snapshot.empty) {
    sendJson(res, 404, { ok: false, error: "no turns yet" });
    return;
  }
  const doc = snapshot.docs[0];
  sendJson(res, 200, { ok: true, data: { id: doc.id, ...doc.data() } });
}

async function handleTurnGet(
  url: URL,
  res: http.ServerResponse
): Promise<void> {
  const db = await requireFirestore(res);
  if (!db) return;
  const game = url.searchParams.get("gameId") || gameId;
  const turnKey = url.searchParams.get("turnKey");
  if (!game || !turnKey) {
    sendJson(res, 400, { ok: false, error: "gameId and turnKey required" });
    return;
  }
  const docId = `${game}-${turnKey}`;
  const doc = await db.collection(firestoreCollection).doc(docId).get();
  if (!doc.exists) {
    sendJson(res, 404, { ok: false, error: "turn not found" });
    return;
  }
  sendJson(res, 200, { ok: true, data: { id: doc.id, ...doc.data() } });
}

async function handleTurnRange(
  url: URL,
  res: http.ServerResponse
): Promise<void> {
  const db = await requireFirestore(res);
  if (!db) return;
  const game = url.searchParams.get("gameId") || gameId;
  const limit = Math.min(Number(url.searchParams.get("limit") || "20"), 200);
  if (!game) {
    sendJson(res, 400, { ok: false, error: "gameId required" });
    return;
  }
  const snapshot = await db
    .collection(firestoreCollection)
    .where("gameId", "==", game)
    .orderBy("observedAt", "desc")
    .limit(limit)
    .get();
  const items = snapshot.docs.map((doc: any) => ({
    id: doc.id,
    ...doc.data(),
  }));
  sendJson(res, 200, { ok: true, data: { count: items.length, items } });
}

async function startHttp() {
  const server = http.createServer(async (req, res) => {
    if (!req.url) {
      sendJson(res, 400, { ok: false, error: "missing url" });
      return;
    }
    const url = new URL(req.url, "http://localhost");
    try {
      if (url.pathname === "/health") {
        res.writeHead(200, { "Content-Type": "text/plain" });
        res.end("ok");
        return;
      }
      if (url.pathname === "/turn/status" || url.pathname === "/turn/latest") {
        await handleTurnLatest(url, res);
        return;
      }
      if (url.pathname === "/turn/get") {
        await handleTurnGet(url, res);
        return;
      }
      if (url.pathname === "/turn/range") {
        await handleTurnRange(url, res);
        return;
      }
      sendJson(res, 404, { ok: false, error: "not found" });
    } catch (err: any) {
      console.error("[turn-relay] http handler error", err);
      sendJson(res, 500, { ok: false, error: err?.message || "server error" });
    }
  });

  server.listen(port, () => {
    console.log(`[turn-relay] HTTP server listening on :${port}`);
  });
}

startRelay().catch((err) => {
  console.error("[turn-relay] fatal error", err);
  process.exit(1);
});

startHttp().catch((err) => {
  console.error("[turn-relay] http server failed", err);
  process.exit(1);
});

