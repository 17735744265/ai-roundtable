import { useEffect, useRef, useState, useCallback } from 'react';
import { sseUrl } from '../api/client';
import type { SSEEvent, SSEEventType } from '../types';

interface UseSSEOptions {
  onEvent: (event: SSEEvent) => void;
  enabled: boolean;
}

export function useSSE(sessionId: string | null, options: UseSSEOptions) {
  const { onEvent, enabled } = options;
  const [connectionState, setConnectionState] = useState<'connecting' | 'open' | 'closed' | 'error' | 'done'>('closed');
  const [retryCount, setRetryCount] = useState(0);
  const eventSourceRef = useRef<EventSource | null>(null);
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const connectionRef = useRef<'open' | 'closed' | 'done'>('closed');

  const connect = useCallback(() => {
    if (!sessionId || !enabled) return;

    // Close existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    setConnectionState('connecting');
    const url = sseUrl(`/discussion/${sessionId}/stream`);
    const es = new EventSource(url);
    eventSourceRef.current = es;

    es.onopen = () => {
      connectionRef.current = 'open';
      setConnectionState('open');
      setRetryCount(0);
    };

    // Register handlers for all event types
    const eventTypes: SSEEventType[] = [
      'connected', 'phase_start', 'moderator_opening', 'guest_statement',
      'free_discussion', 'moderator_summary', 'phase_end',
      'session_end', 'done', 'error',
    ];

    for (const type of eventTypes) {
      es.addEventListener(type, (e: MessageEvent) => {
        try {
          const data = JSON.parse(e.data);
          onEvent({ type, data });
        } catch {
          // Ignore parse errors
        }
        // Mark stream as gracefully ended on terminal events
        if (type === 'done' || type === 'session_end' || type === 'moderator_summary') {
          connectionRef.current = 'done';
        }
      });
    }

    es.onerror = () => {
      // If we've received terminal events, don't retry
      if (connectionRef.current === 'done') {
        es.close();
        setConnectionState('done');
        return;
      }

      es.close();
      setConnectionState('error');

      // Auto-retry with backoff for transient errors
      if (retryCount < 3) {
        const delay = Math.min(1000 * Math.pow(2, retryCount), 8000);
        retryTimerRef.current = setTimeout(() => {
          setRetryCount((c) => c + 1);
          connect();
        }, delay);
      }
    };
  }, [sessionId, enabled, onEvent, retryCount]);

  const disconnect = useCallback(() => {
    if (retryTimerRef.current) {
      clearTimeout(retryTimerRef.current);
    }
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setConnectionState('closed');
  }, []);

  useEffect(() => {
    if (enabled && sessionId) {
      connect();
    }
    return () => disconnect();
  }, [sessionId, enabled]);

  return {
    connectionState,
    retryCount,
    reconnect: connect,
    disconnect,
  };
}
