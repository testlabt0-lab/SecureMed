import { useEffect, useState, useCallback } from 'react';
import { notificationsApi } from '../api/extendedApis';

interface Notification {
  id: number;
  type: string;
  message: string;
  is_read: boolean;
  created_at: string;
}

interface WebSocketMessage {
  type: 'initial_unread_count' | 'new_notification' | 'unread_count_updated';
  unread_count?: number;
  notification?: Notification;
}

/**
 * Hook for real-time notifications using WebSocket
 * Falls back to polling if WebSocket is not available
 */
export function useRealtimeNotifications() {
  const [unreadCount, setUnreadCount] = useState(0);
  const [isConnected, setIsConnected] = useState(false);

  // Fetch initial unread count
  const fetchUnreadCount = useCallback(async () => {
    try {
      const response = await notificationsApi.unreadCount();
      setUnreadCount(response.data?.unread_count || 0);
    } catch (error) {
      console.error('Failed to fetch unread count:', error);
    }
  }, []);

  useEffect(() => {
    // Initial fetch
    fetchUnreadCount();

    // Try to establish WebSocket connection
    let ws: WebSocket | null = null;
    let reconnectTimeout: NodeJS.Timeout;

    const connectWebSocket = () => {
      try {
        // Get the WebSocket URL from the current location
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/notifications/`;

        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
          console.log('WebSocket connected for notifications');
          setIsConnected(true);
        };

        ws.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data);
            
            switch (message.type) {
              case 'initial_unread_count':
                setUnreadCount(message.unread_count || 0);
                break;
              case 'new_notification':
                // Optionally handle new notification here
                fetchUnreadCount(); // Refresh the count
                break;
              case 'unread_count_updated':
                setUnreadCount(message.unread_count || 0);
                break;
            }
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };

        ws.onclose = () => {
          console.log('WebSocket disconnected, attempting to reconnect...');
          setIsConnected(false);
          // Reconnect after 5 seconds
          reconnectTimeout = setTimeout(connectWebSocket, 5000);
        };

        ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          ws?.close();
        };
      } catch (error) {
        console.error('Failed to establish WebSocket connection, falling back to polling:', error);
        // Fallback to polling if WebSocket fails
        const pollInterval = setInterval(fetchUnreadCount, 30000);
        return () => clearInterval(pollInterval);
      }
    };

    connectWebSocket();

    // Cleanup function
    return () => {
      if (ws) {
        ws.close();
      }
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
      }
    };
  }, [fetchUnreadCount]);

  return {
    unreadCount,
    isConnected,
  };
}

/**
 * Hook for recent notifications with real-time updates
 */
export function useRecentNotifications(limit = 5) {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchNotifications = useCallback(async () => {
    try {
      const response = await notificationsApi.list({ page_size: limit });
      const results = response.data?.results || response.data || [];
      setNotifications(results.slice(0, limit));
    } catch (error) {
      console.error('Failed to fetch notifications:', error);
    } finally {
      setIsLoading(false);
    }
  }, [limit]);

  useEffect(() => {
    fetchNotifications();

    // Set up WebSocket for real-time updates
    let ws: WebSocket | null = null;

    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws/notifications/`;
      
      ws = new WebSocket(wsUrl);

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          
          if (message.type === 'new_notification') {
            // Refresh the notifications list when a new one arrives
            fetchNotifications();
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error for recent notifications:', error);
      };
    } catch (error) {
      console.warn('WebSocket not available for recent notifications, using polling fallback');
      // Fallback to polling every 60 seconds
      const pollInterval = setInterval(fetchNotifications, 60000);
      return () => clearInterval(pollInterval);
    }

    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, [fetchNotifications]);

  return {
    notifications,
    isLoading,
  };
}
