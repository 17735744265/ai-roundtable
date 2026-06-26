import React, { createContext, useContext, useReducer, useCallback } from 'react';
import type { DiscussionState, DiscussionPhase, Message, SSEEvent, ExpertStatusMap } from '../types';

type Action =
  | { type: 'CONNECTED'; sessionId: string; topic: string }
  | { type: 'PHASE_START'; phase: DiscussionPhase; round: number }
  | { type: 'ADD_MESSAGE'; message: Message }
  | { type: 'MESSAGE_START'; speakerId: string; speakerName: string; phase: string; msgId: string }
  | { type: 'MESSAGE_CHUNK'; msgId: string; contentDelta: string; speakerId: string }
  | { type: 'SESSION_END'; consensus?: string[]; divergence?: string[] }
  | { type: 'EXPERT_STATUS'; status: ExpertStatusMap }
  | { type: 'CONSENSUS_UPDATE'; allConsensus: string[]; allDivergence: string[] }
  | { type: 'ERROR'; error: string };

function createInitialState(): DiscussionState {
  return {
    sessionId: '', topic: '', phase: 'connecting', currentRound: 0,
    messages: [], isConnected: false, error: null,
    expertStatus: {}, consensusPoints: [], divergencePoints: [],
    pendingSpeakerId: null, pendingContent: '',
  };
}

function reducer(state: DiscussionState, action: Action): DiscussionState {
  switch (action.type) {
    case 'CONNECTED':
      return { ...state, sessionId: action.sessionId, topic: action.topic, isConnected: true, error: null };
    case 'PHASE_START':
      return { ...state, phase: action.phase, currentRound: action.round };
    case 'ADD_MESSAGE':
      // Replace pending placeholder or add new
      return {
        ...state,
        messages: [...state.messages, action.message],
        pendingSpeakerId: null,
        pendingContent: '',
      };
    case 'MESSAGE_START':
      return {
        ...state,
        pendingSpeakerId: action.speakerId,
        pendingContent: '',
      };
    case 'MESSAGE_CHUNK':
      return {
        ...state,
        pendingContent: state.pendingContent + action.contentDelta,
      };
    case 'SESSION_END':
      return { ...state, phase: 'completed',
        consensusPoints: action.consensus || state.consensusPoints,
        divergencePoints: action.divergence || state.divergencePoints,
      };
    case 'EXPERT_STATUS':
      return { ...state, expertStatus: { ...state.expertStatus, ...action.status } };
    case 'CONSENSUS_UPDATE':
      return { ...state, consensusPoints: action.allConsensus, divergencePoints: action.allDivergence };
    case 'ERROR':
      return { ...state, phase: 'error', error: action.error, isConnected: false };
    default:
      return state;
  }
}

interface RoundtableContextValue {
  state: DiscussionState;
  processSSEEvent: (event: SSEEvent) => void;
}

const RoundtableContext = createContext<RoundtableContextValue | null>(null);

export function RoundtableProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(reducer, null, createInitialState);

  const processSSEEvent = useCallback((event: SSEEvent) => {
    switch (event.type) {
      case 'connected':
        dispatch({ type: 'CONNECTED', sessionId: event.data.session_id || '', topic: event.data.topic || '' });
        break;
      case 'phase_start':
        dispatch({ type: 'PHASE_START', phase: (event.data.phase as DiscussionPhase) || 'opening', round: event.data.round || 0 });
        break;
      case 'message_start':
        dispatch({
          type: 'MESSAGE_START',
          speakerId: event.data.speaker_id || '',
          speakerName: event.data.speaker_name || '',
          phase: event.data.phase || 'free_discussion',
          msgId: event.data.id || '',
        });
        break;

      case 'message_chunk':
        dispatch({
          type: 'MESSAGE_CHUNK',
          msgId: event.data.id || '',
          contentDelta: event.data.content_delta || '',
          speakerId: event.data.speaker_id || '',
        });
        break;

      case 'moderator_opening':
      case 'free_discussion':
      case 'moderator_summary':
      case 'moderator_connect':
        dispatch({ type: 'ADD_MESSAGE', message: {
          id: event.data.id || crypto.randomUUID(),
          session_id: event.data.session_id || state.sessionId,
          phase: (event.data.phase as Message['phase']) || 'free_discussion',
          round: event.data.round || 0,
          speaker_id: event.data.speaker_id || '',
          speaker_name: event.data.speaker_name || '',
          content: event.data.content || '',
          sequence: state.messages.length + 1,
          created_at: new Date().toISOString(),
        }});
        break;
      case 'session_end':
        dispatch({ type: 'SESSION_END', consensus: event.data.consensus, divergence: event.data.divergence });
        break;
      case 'expert_status':
        if (event.data.status) {
          dispatch({ type: 'EXPERT_STATUS', status: event.data.status });
        }
        break;
      case 'consensus_update':
        dispatch({ type: 'CONSENSUS_UPDATE', allConsensus: event.data.all_consensus || [], allDivergence: event.data.all_divergence || [] });
        break;
      case 'error':
        dispatch({ type: 'ERROR', error: event.data.message || event.data.code || '未知错误' });
        break;
      case 'done':
      case 'phase_end':
        break;
    }
  }, [state.sessionId, state.messages.length]);

  return (
    <RoundtableContext.Provider value={{ state, processSSEEvent }}>
      {children}
    </RoundtableContext.Provider>
  );
}

export function useRoundtable(): RoundtableContextValue {
  const ctx = useContext(RoundtableContext);
  if (!ctx) throw new Error('useRoundtable must be used within RoundtableProvider');
  return ctx;
}
