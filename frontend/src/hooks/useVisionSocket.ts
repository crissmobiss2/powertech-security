import { useEffect, useRef, useState, useCallback } from "react";
import { getAccessToken } from "@/lib/auth";

export interface VisionEvent {
  id: string;
  type: string;
  payload: Record<string, unknown>;
  timestamp: string;
  read: boolean;
}

interface UseVisionSocketOptions {
  onThreat?: (event: VisionEvent) => void;
  onFace?: (event: VisionEvent) => void;
  onCameraStatus?: (event: VisionEvent) => void;
  enabled?: boolean;
}

export function useVisionSocket(options: UseVisionSocketOptions = {}) {
  const { onThreat, onFace, onCameraStatus, enabled = true } = options;
  const [connected, setConnected] = useState(false);
  const [events, setEvents] = useState<VisionEvent[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<ReturnType<typeof setTimeout>>();
  const pingInterval = useRef<ReturnType<typeof setInterval>>();
  const mountedRef = useRef(true);

  const addEvent = useCallback((evt: VisionEvent) => {
    setEvents((prev) => [evt, ...prev].slice(0, 100));
  }, []);

  const clearEvents = useCallback(() => {
    setEvents([]);
  }, []);

  const markRead = useCallback((id: string) => {
    setEvents((prev) =>
      prev.map((e) => (e.id === id ? { ...e, read: true } : e))
    );
  }, []);

  const unreadCount = events.filter((e) => !e.read).length;

  useEffect(() => {
    mountedRef.current = true;
    if (!enabled) return;

    let attempt = 0;

    function connect() {
      const token = getAccessToken();
      if (!token) return;

      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const host = apiUrl.replace(/^https?:\/\//, "");
      const url = `${protocol}//${host}/api/v1/ws/vision/live?token=${token}`;

      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!mountedRef.current) return;
        setConnected(true);
        attempt = 0;
        pingInterval.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send("ping");
          }
        }, 30_000);
      };

      ws.onmessage = (msg) => {
        if (!mountedRef.current) return;
        try {
          const data = JSON.parse(msg.data);
          if (data.type === "pong") return;

          const event: VisionEvent = {
            id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
            type: data.type,
            payload: data.payload || {},
            timestamp: data.timestamp || new Date().toISOString(),
            read: false,
          };

          addEvent(event);

          if (
            data.type === "threat_detected" ||
            data.type === "banned_person"
          ) {
            onThreat?.(event);
          } else if (data.type === "face_detected") {
            onFace?.(event);
          } else if (data.type === "camera_status") {
            onCameraStatus?.(event);
          }
        } catch {
          // ignore malformed messages
        }
      };

      ws.onclose = () => {
        if (!mountedRef.current) return;
        setConnected(false);
        if (pingInterval.current) clearInterval(pingInterval.current);
        attempt++;
        const delay = Math.min(1000 * 2 ** attempt, 30_000);
        reconnectTimeout.current = setTimeout(connect, delay);
      };

      ws.onerror = () => {
        ws.close();
      };
    }

    connect();

    return () => {
      mountedRef.current = false;
      if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
      if (pingInterval.current) clearInterval(pingInterval.current);
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
      }
    };
  }, [enabled, onThreat, onFace, onCameraStatus, addEvent]);

  return { connected, events, unreadCount, clearEvents, markRead };
}
