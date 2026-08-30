import { useQuery } from '@tanstack/react-query';
import { notificationsApi } from '../api/extendedApis';

/**
 * Hook for real-time notification polling.
 * Returns unread count that auto-refreshes every 30 seconds.
 */
export function useRealtimeNotifications() {
  const { data } = useQuery({
    queryKey: ['unread-count'],
    queryFn: () => notificationsApi.unreadCount(),
    refetchInterval: 30000,
    refetchOnWindowFocus: true,
  });

  return {
    unreadCount: data?.data?.unread_count || 0,
  };
}

/**
 * Hook for polling recent notifications.
 */
export function useRecentNotifications(limit = 5) {
  return useQuery({
    queryKey: ['recent-notifications', limit],
    queryFn: () => notificationsApi.list({ page_size: limit }),
    refetchInterval: 60000,
    select: (data) => {
      const results = data.data?.results || data.data || [];
      return results.slice(0, limit);
    },
  });
}
