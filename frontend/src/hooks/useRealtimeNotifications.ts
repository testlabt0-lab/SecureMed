import { useEffect, useRef } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { notificationsApi } from '../api/extendedApis';

export function useRealtimeNotifications() {
  const queryClient = useQueryClient();
  const wsRef = useRef<WebSocket | null>(null);

  // Initial fetch for count
  const { data } = useQuery({
    queryKey: ['unread-count'],
    queryFn: () => notificationsApi.unreadCount(),
    refetchOnWindowFocus: true,
  });

  useEffect(() => {
    // Determine WS protocol
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    // Use window.location.host, but fallback to localhost:8000 for local dev if needed
    // Usually Vite proxy isn't setup for WS in default setup, but let's assume standard URL or hardcode for dev:
    const host = process.env.NODE_ENV === 'development' ? 'localhost:8000' : window.location.host;
    
    // Check if token exists to pass (if using token-based WS auth, but channels might use session)
    const token = localStorage.getItem('access_token');
    // Using a query param for token if backend supports it, otherwise standard connection
    const wsUrl = `${protocol}//${host}/ws/notifications/${token ? `?token=${token}` : ''}`;

    const connectWs = () => {
      const ws = new WebSocket(wsUrl);
      
      ws.onopen = () => {
        console.log('Connected to real-time notifications');
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          if (message.type === 'notification') {
            // Invalidate queries so UI updates instantly
            queryClient.invalidateQueries({ queryKey: ['unread-count'] });
            queryClient.invalidateQueries({ queryKey: ['recent-notifications'] });
          }
        } catch (e) {
          console.error('Error parsing WS message', e);
        }
      };

      ws.onclose = () => {
        console.log('Disconnected from real-time notifications. Reconnecting in 5s...');
        setTimeout(connectWs, 5000);
      };
      
      wsRef.current = ws;
    };

    connectWs();

    return () => {
      if (wsRef.current) {
        wsRef.current.onclose = null; // prevent reconnect on unmount
        wsRef.current.close();
      }
    };
  }, [queryClient]);

  return {
    unreadCount: data?.data?.unread_count || 0,
  };
}

/**
 * Hook for recent notifications.
 */
export function useRecentNotifications(limit = 5) {
  return useQuery({
    queryKey: ['recent-notifications', limit],
    queryFn: () => notificationsApi.list({ page_size: limit }),
    select: (data) => {
      const results = data.data?.results || data.data || [];
      return results.slice(0, limit);
    },
  });
}
