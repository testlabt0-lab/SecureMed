import { useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../store/authStore';

/**
 * Live notification socket.
 *
 * This hook was dead code and would not have worked if it had been wired up: it
 * read the access token from `localStorage`, where this app has never kept it
 * (Zustand persists to `sessionStorage`), so the socket connected anonymously. The
 * backend answered in kind — `NotificationConsumer` accepted anonymous handshakes
 * and joined no group — so the connection stayed open and silent forever. Both
 * halves are fixed: the token comes from the store, and the consumer now closes
 * anonymous handshakes with 4001.
 *
 * The token travels as a WebSocket subprotocol rather than `?token=`, because query
 * strings are written to proxy access logs and a logged access token is a
 * credential at rest. `Sec-WebSocket-Protocol` is the only client-controlled
 * request header the browser WebSocket API exposes.
 *
 * The hook owns the socket only. The unread count itself stays a React Query cache
 * entry owned by whoever displays it — this just invalidates it on push, so the
 * badge updates from one code path whether the number arrived by socket or by the
 * fallback poll.
 */

/** Server-sent close code meaning "the token was refused"; see the consumer. */
const CLOSE_UNAUTHENTICATED = 4001;
const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 30000;
/** Idle sockets are dropped by many reverse proxies at 60s. */
const PING_INTERVAL_MS = 30000;

export type SocketState = 'idle' | 'connecting' | 'open' | 'closed' | 'unauthorised';

export function useRealtimeNotifications() {
  const queryClient = useQueryClient();
  const accessToken = useAuthStore((s) => s.accessToken);
  const [state, setState] = useState<SocketState>('idle');

  const socketRef = useRef<WebSocket | null>(null);
  const retryRef = useRef(0);
  const timersRef = useRef<{ reconnect?: number; ping?: number }>({});

  useEffect(() => {
    if (!accessToken) {
      setState('idle');
      return;
    }

    let disposed = false;

    const clearTimers = () => {
      if (timersRef.current.reconnect) window.clearTimeout(timersRef.current.reconnect);
      if (timersRef.current.ping) window.clearInterval(timersRef.current.ping);
      timersRef.current = {};
    };

    const connect = () => {
      if (disposed) return;

      const scheme = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      setState('connecting');

      let socket: WebSocket;
      try {
        socket = new WebSocket(
          `${scheme}//${window.location.host}/ws/notifications/`,
          ['access_token', accessToken],
        );
      } catch {
        setState('closed');
        return;
      }
      socketRef.current = socket;

      socket.onopen = () => {
        if (disposed) return;
        retryRef.current = 0;
        setState('open');
        timersRef.current.ping = window.setInterval(() => {
          if (socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ action: 'ping' }));
          }
        }, PING_INTERVAL_MS);
      };

      socket.onmessage = (event) => {
        let message: any;
        try {
          message = JSON.parse(event.data);
        } catch {
          return;
        }
        if (message?.type !== 'notification') return;
        queryClient.invalidateQueries({ queryKey: ['unread-count'] });
        queryClient.invalidateQueries({ queryKey: ['recent-notifications'] });
        queryClient.invalidateQueries({ queryKey: ['notifications'] });
      };

      socket.onclose = (event) => {
        if (timersRef.current.ping) window.clearInterval(timersRef.current.ping);
        if (disposed) return;

        // A refused token will be refused again on every retry, so reconnecting is
        // a hot loop against the auth path. The axios interceptor refreshes the
        // token on the next API call; that changes `accessToken`, which re-runs
        // this effect — the only thing that should reopen the socket.
        if (event.code === CLOSE_UNAUTHENTICATED) {
          setState('unauthorised');
          return;
        }

        setState('closed');
        const delay = Math.min(RECONNECT_BASE_MS * 2 ** retryRef.current, RECONNECT_MAX_MS);
        retryRef.current += 1;
        timersRef.current.reconnect = window.setTimeout(connect, delay);
      };
    };

    connect();

    return () => {
      disposed = true;
      clearTimers();
      const socket = socketRef.current;
      socketRef.current = null;
      if (socket) {
        socket.onclose = null; // our own teardown must not schedule a reconnect
        socket.close();
      }
    };
  }, [accessToken, queryClient]);

  return { state, connected: state === 'open' };
}
