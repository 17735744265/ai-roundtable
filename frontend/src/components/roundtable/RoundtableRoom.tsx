import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSSE } from '../../hooks/useSSE';
import { useRoundtable } from '../../store/roundtable-context';
import { MessageBubble } from './MessageBubble';
import type { SSEEvent, Message, ExpertStatusMap } from '../../types';

interface RoundtableRoomProps {
  sessionId: string;
}

export function RoundtableRoom({ sessionId }: RoundtableRoomProps) {
  const navigate = useNavigate();
  const { state, processSSEEvent } = useRoundtable();
  const [lastSpeakerId, setLastSpeakerId] = useState<string | null>(null);
  const [newMsgIds, setNewMsgIds] = useState<Set<string>>(new Set());
  const [changedExperts, setChangedExperts] = useState<Set<string>>(new Set());
  const [guestMeta, setGuestMeta] = useState<Record<string, { name: string; title: string; color: string; avatar: string }>>({});
  const transcriptRef = useRef<HTMLDivElement>(null);

  const { connectionState } = useSSE(sessionId, {
    onEvent: (event: SSEEvent) => {
      processSSEEvent(event);
      if (event.type === 'expert_status' && event.data.status) {
        const changed = Object.keys(event.data.status);
        setChangedExperts(new Set(changed));
        setTimeout(() => setChangedExperts(new Set()), 800);
      }
      if (event.type === 'moderator_opening' || event.type === 'free_discussion' || event.type === 'moderator_summary') {
        setLastSpeakerId(event.data.speaker_id || null);
        if (event.data.id) {
          setNewMsgIds(prev => { const n = new Set(prev); n.add(event.data.id!); return n; });
          setTimeout(() => setNewMsgIds(prev => { const n = new Set(prev); n.delete(event.data.id!); return n; }), 500);
        }
      }
    },
    enabled: true,
  });

  useEffect(() => {
    import('../../api/sessions').then(({ fetchSession }) => {
      fetchSession(sessionId).then(s => {
        const meta: Record<string, any> = {};
        for (const g of s.guests) meta[g.id] = { name: g.name, title: g.title, color: g.color, avatar: g.avatar };
        setGuestMeta(meta);
      }).catch(() => {});
    });
  }, [sessionId]);

  // Auto-scroll transcript
  useEffect(() => {
    if (transcriptRef.current) {
      transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight;
    }
  }, [state.messages.length]);

  const isCompleted = state.phase === 'completed';
  const isLive = !isCompleted && state.phase !== 'error' && state.phase !== 'connecting';
  const visibleMsgs = state.messages.filter((m: Message) =>
    m.phase === 'opening' || m.phase === 'free_discussion' || m.phase === 'summary'
  );

  return (
    <div className="studio-layout bg-slate-950">
      {/* ═══ Header ═══ */}
      <header className="studio-header bg-slate-900/95 backdrop-blur-md border-b border-slate-700/30">
        <div className="px-4 py-2.5 flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${isLive ? 'bg-red-500 on-air-dot' : isCompleted ? 'bg-emerald-500' : 'bg-slate-500'}`} />
            <span className="text-[10px] font-bold text-slate-500 tracking-widest uppercase">
              {isLive ? 'ON AIR' : isCompleted ? 'ENDED' : 'STANDBY'}
            </span>
          </div>
          <div className="flex-1 min-w-0">
            <h1 className="text-sm font-bold text-white truncate">{state.topic || 'AI 圆桌讨论'}</h1>
          </div>
          {/* Mini guest chips */}
          <div className="hidden sm:flex items-center gap-1">
            {Object.entries(guestMeta).filter(([id]) => id !== 'moderator').slice(0, 4).map(([id, m]) => {
              const status = state.expertStatus[id];
              const isUp = status?.state === 'speaking' || status?.state === 'ready';
              return (
                <div key={id} className={`flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] transition-colors ${isUp ? 'bg-blue-500/15 text-blue-300' : 'text-slate-500'}`}>
                  <span className="text-xs">{m.avatar}</span>
                  <span className="hidden lg:inline truncate max-w-[60px]">{m.name}</span>
                </div>
              );
            })}
          </div>
        </div>
      </header>

      {/* ═══ Main Area ═══ */}
      <div className="studio-main">
        {/* ── Expert Sidebar ── */}
        <aside className="studio-sidebar w-44 xl:w-52 flex-shrink-0 border-r border-slate-800/50 bg-slate-950/50 hidden lg:flex flex-col">
          <div className="px-3 py-2 border-b border-slate-800/50">
            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">专家状态</p>
          </div>
          <div className="flex-1 scroll-container">
            {Object.entries(guestMeta).filter(([id]) => id !== 'moderator').map(([id, m]) => {
              const status = state.expertStatus[id] || { state: 'idle', focus: '等待开始...' };
              const s = status.state;
              const dotColor = s === 'speaking' ? 'bg-blue-400' : s === 'ready' ? 'bg-emerald-400' : s === 'preparing' ? 'bg-yellow-400 status-preparing' : 'bg-slate-700';
              const borderColor = s === 'speaking' ? 'border-blue-500/20 bg-blue-500/5' : s === 'ready' ? 'border-emerald-500/10 bg-emerald-500/3' : 'border-transparent';

              return (
                <div key={id} className={`px-3 py-2.5 border-b border-slate-800/30 transition-all duration-300 ${borderColor} ${changedExperts.has(id) ? 'expert-status-changed' : ''}`}>
                  <div className="flex items-center gap-1.5 mb-0.5">
                    <div className={`w-1.5 h-1.5 rounded-full ${dotColor}`}
                         style={s === 'speaking' ? { boxShadow: `0 0 6px ${m.color}` } : {}} />
                    <span className="text-xs">{m.avatar}</span>
                    <span className="text-[11px] text-slate-300 font-medium truncate">{m.name}</span>
                    <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ backgroundColor: m.color }} />
                  </div>
                  <p className="text-[9px] text-slate-600 truncate ml-5">{m.title}</p>
                  <p className={`text-[9px] mt-0.5 ml-5 truncate transition-colors ${s === 'speaking' ? 'text-blue-400 font-medium' : s === 'preparing' ? 'text-yellow-400/70' : 'text-slate-600'}`}>
                    {status.focus || '聆听中'}
                  </p>
                </div>
              );
            })}
          </div>
        </aside>

        {/* ── Transcript ── */}
        <main ref={transcriptRef} className="studio-transcript scroll-container px-4 py-4">
          <div className="max-w-2xl mx-auto space-y-3">
            {/* Empty */}
            {visibleMsgs.length === 0 && !state.error && (
              <div className="flex flex-col items-center justify-center py-32 gap-3 text-center">
                <div className="text-5xl animate-bounce">🎙️</div>
                <p className="text-slate-500 text-sm">{connectionState === 'connecting' ? '正在进入演播厅...' : '等待讨论开始...'}</p>
              </div>
            )}

            {visibleMsgs.map((msg: Message) => {
              const meta = guestMeta[msg.speaker_id];
              return (
                <MessageBubble
                  key={msg.id}
                  message={msg}
                  isSpeaking={false}
                  isNew={newMsgIds.has(msg.id)}
                  guestTitle={meta?.title || ''}
                  guestColor={meta?.color || '#94A3B8'}
                />
              );
            })}

            {/* Streaming: pending content from current speaker */}
            {state.pendingSpeakerId && state.pendingContent && (
              <div className="flex gap-3">
                <div className="flex-shrink-0 pt-0.5">
                  <div className="w-8 h-8 rounded-full flex items-center justify-center text-base bg-slate-700/50 avatar-breathing" />
                </div>
                <div className="flex-1 min-w-0 rounded-xl px-3.5 py-2.5 border bg-slate-800/30 border-slate-700/40"
                     style={{ borderLeftColor: guestMeta[state.pendingSpeakerId]?.color || '#3B82F6', borderLeftWidth: '2px' }}>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-semibold text-slate-200">{guestMeta[state.pendingSpeakerId]?.name || '...'}</span>
                    <span className="text-[10px] text-slate-500">{guestMeta[state.pendingSpeakerId]?.title || ''}</span>
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed whitespace-pre-wrap">
                    {state.pendingContent}
                    <span className="inline-block w-1.5 h-4 bg-blue-400 animate-pulse ml-0.5 align-middle" />
                  </p>
                </div>
              </div>
            )}

            {/* Streaming: waiting for first chunk */}
            {state.pendingSpeakerId && !state.pendingContent && (
              <div className="flex gap-3">
                <div className="flex-shrink-0 pt-0.5">
                  <div className="w-8 h-8 rounded-full flex items-center justify-center text-base bg-slate-700/50 avatar-breathing" />
                </div>
                <div className="flex-1 min-w-0 rounded-xl px-3.5 py-3 border bg-slate-800/30 border-slate-700/40">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-400">正在生成...</span>
                    <span className="flex gap-1">
                      <span className="w-1 h-1 rounded-full bg-slate-500 animate-bounce" style={{ animationDelay: '0ms' }} />
                      <span className="w-1 h-1 rounded-full bg-slate-500 animate-bounce" style={{ animationDelay: '150ms' }} />
                      <span className="w-1 h-1 rounded-full bg-slate-500 animate-bounce" style={{ animationDelay: '300ms' }} />
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Error */}
            {state.error && (
              <div className="p-6 rounded-2xl border border-red-500/20 bg-red-500/5">
                <p className="text-red-400 font-semibold text-sm mb-1">⚠️ 讨论中断</p>
                <p className="text-red-300/70 text-xs">{state.error}</p>
              </div>
            )}

            {/* Summary */}
            {isCompleted && state.messages.length > 0 && (
              <div className="rounded-2xl border border-emerald-500/15 bg-emerald-500/3 p-5 mt-6">
                <div className="flex items-center gap-2 mb-4">
                  <span className="text-lg">✅</span>
                  <div>
                    <h3 className="text-sm font-bold text-emerald-300">讨论结束</h3>
                    <p className="text-[10px] text-emerald-400/60">
                      {state.messages.length} 条 · {state.consensusPoints.length} 共识 · {state.divergencePoints.length} 分歧
                    </p>
                  </div>
                </div>
                {state.consensusPoints.length > 0 && (
                  <div className="mb-3">
                    <div className="text-[10px] font-bold text-emerald-400 mb-1.5 uppercase tracking-wide">共识</div>
                    {state.consensusPoints.map((p, i) => (
                      <div key={i} className="text-[11px] text-emerald-300/70 flex gap-1.5 mb-0.5"><span>·</span>{p}</div>
                    ))}
                  </div>
                )}
                {state.divergencePoints.length > 0 && (
                  <div>
                    <div className="text-[10px] font-bold text-orange-400 mb-1.5 uppercase tracking-wide">分歧</div>
                    {state.divergencePoints.map((p, i) => (
                      <div key={i} className="text-[11px] text-orange-300/70 flex gap-1.5 mb-0.5"><span>·</span>{p}</div>
                    ))}
                  </div>
                )}
              </div>
            )}

            <div className="h-1" /> {/* Bottom spacer */}
          </div>
        </main>

        {/* ── Consensus Sidebar ── */}
        <aside className="studio-sidebar w-48 xl:w-56 flex-shrink-0 border-l border-slate-800/50 bg-slate-950/50 hidden xl:flex flex-col">
          <div className="px-3 py-2 border-b border-slate-800/50 flex items-center justify-between">
            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">实时追踪</p>
            <span className="text-[9px] text-slate-600">
              {(state.consensusPoints.length + state.divergencePoints.length) || ''}
            </span>
          </div>
          <div className="flex-1 scroll-container p-2 space-y-2">
            {state.consensusPoints.length === 0 && state.divergencePoints.length === 0 && (
              <p className="text-[10px] text-slate-600 text-center py-8">等待共识/分歧浮现...</p>
            )}
            {state.consensusPoints.length > 0 && (
              <div className="p-2 rounded-lg bg-emerald-500/5 border border-emerald-500/10">
                <div className="text-[10px] font-bold text-emerald-400 mb-1.5 uppercase tracking-wide">
                  ✅ 共识 ({state.consensusPoints.length})
                </div>
                {state.consensusPoints.map((p, i) => (
                  <div key={i}
                    className="text-[10px] text-emerald-300/60 flex gap-1 mb-0.5 consensus-item-enter"
                    style={{ animationDelay: `${i * 50}ms` }}>
                    <span className="text-emerald-500">·</span>{p}
                  </div>
                ))}
              </div>
            )}
            {state.divergencePoints.length > 0 && (
              <div className="p-2 rounded-lg bg-orange-500/5 border border-orange-500/10">
                <div className="text-[10px] font-bold text-orange-400 mb-1.5 uppercase tracking-wide">
                  ⚡ 分歧 ({state.divergencePoints.length})
                </div>
                {state.divergencePoints.map((p, i) => (
                  <div key={i}
                    className="text-[10px] text-orange-300/60 flex gap-1 mb-0.5 consensus-item-enter"
                    style={{ animationDelay: `${i * 50}ms` }}>
                    <span className="text-orange-500">·</span>{p}
                  </div>
                ))}
              </div>
            )}
          </div>
        </aside>
      </div>

      {/* ═══ Footer ═══ */}
      <footer className="studio-footer bg-slate-900/95 backdrop-blur-md border-t border-slate-700/30">
        <div className="px-4 py-2 flex items-center justify-between">
          <div className="flex items-center gap-2 text-[11px] text-slate-500">
            <span>{isLive ? '💬 深度讨论中' : isCompleted ? '✅ 已结束' : state.phase === 'error' ? '⚠️ 中断' : '🔗 连接中...'}</span>
            {state.messages.length > 0 && <span>· {state.messages.length} 条</span>}
          </div>
          <button
            onClick={() => navigate('/')}
            className={`px-4 py-1 rounded-lg text-[11px] font-medium transition-all ${
              isCompleted ? 'bg-slate-800 text-slate-400 hover:bg-slate-700' :
              isLive ? 'bg-red-500/10 border border-red-500/20 text-red-400 hover:bg-red-500/20' :
              'bg-slate-800 text-slate-600'
            }`}
          >
            {isCompleted ? '← 返回首页' : isLive ? '⏹ 离开' : '...'}
          </button>
        </div>
      </footer>
    </div>
  );
}
