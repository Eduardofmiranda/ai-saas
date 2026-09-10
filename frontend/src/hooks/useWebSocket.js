import { useEffect, useRef, useCallback } from "react";

const WS_RECONNECT_DELAY = 3000;

export function useWebSocket(companyId, onEvent) {
  const wsRef = useRef(null);
  const reconnectRef = useRef(null);
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  const connect = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) return;

    const token = localStorage.getItem("token");
    if (!token) return;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const url = `${protocol}//${host}/ws`;

    // Browsers nao permitem header Authorization no handshake WebSocket.
    // O subprotocolo evita expor o JWT em URLs e logs de acesso do proxy.
    const ws = new WebSocket(url, ["access-token", token]);
    wsRef.current = ws;

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        if (msg.event === "pong") return;
        onEventRef.current?.(msg.event, msg.data);
      } catch {}
    };

    ws.onclose = () => {
      wsRef.current = null;
      reconnectRef.current = setTimeout(connect, WS_RECONNECT_DELAY);
    };

    ws.onerror = () => {
      ws.close();
    };

    const pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) ws.send("ping");
    }, 30000);

    ws.addEventListener("close", () => clearInterval(pingInterval));
  }, []);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectRef.current);
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
      }
    };
  }, [connect]);
}
