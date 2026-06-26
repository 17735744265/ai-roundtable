import type { Message } from '../../types';

interface SummaryCardProps {
  messages: Message[];
  topic: string;
  messageCount: number;
  consensusPoints: string[];
  divergencePoints: string[];
}

export function SummaryCard({ messages, topic, messageCount, consensusPoints, divergencePoints }: SummaryCardProps) {
  const summaryMsg = [...messages].reverse().find(
    (m) => m.phase === 'summary' && m.speaker_id === 'moderator'
  );

  // Count per speaker
  const speakerCounts: Record<string, number> = {};
  for (const m of messages) {
    if (m.speaker_id !== 'moderator') {
      speakerCounts[m.speaker_name] = (speakerCounts[m.speaker_name] || 0) + 1;
    }
  }

  const phaseCounts = {
    opening: messages.filter((m) => m.phase === 'opening').length,
    statements: messages.filter((m) => m.phase === 'statements').length,
    free_discussion: messages.filter((m) => m.phase === 'free_discussion').length,
    summary: messages.filter((m) => m.phase === 'summary').length,
  };

  return (
    <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/5 overflow-hidden mt-8">
      {/* Header */}
      <div className="px-6 py-4 bg-emerald-500/10 border-b border-emerald-500/20">
        <div className="flex items-center gap-2">
          <span className="text-2xl">✅</span>
          <div>
            <h3 className="text-lg font-bold text-emerald-300">讨论结束</h3>
            <p className="text-sm text-emerald-400/70 mt-0.5">以下为本次圆桌讨论总结</p>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="px-6 py-4 grid grid-cols-4 gap-4 border-b border-emerald-500/10">
        <StatBox label="总发言" value={String(messageCount)} />
        <StatBox label="开场" value={String(phaseCounts.opening)} />
        <StatBox label="陈述" value={String(phaseCounts.statements)} />
        <StatBox label="讨论" value={String(phaseCounts.free_discussion)} />
      </div>

      {/* Consensus & Divergence */}
      <div className="px-6 py-4 grid grid-cols-2 gap-4 border-b border-emerald-500/10">
        <div className="p-3 rounded-xl bg-emerald-500/8 border border-emerald-500/15">
          <div className="text-xs font-semibold text-emerald-400 mb-1.5">✅ 达成共识</div>
          {consensusPoints.length > 0 ? (
            <ul className="space-y-1">
              {consensusPoints.map((p, i) => (
                <li key={i} className="text-xs text-emerald-300/70 flex gap-1.5">
                  <span className="text-emerald-500">·</span> {p}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-slate-500">讨论未形成明确共识</p>
          )}
        </div>
        <div className="p-3 rounded-xl bg-orange-500/8 border border-orange-500/15">
          <div className="text-xs font-semibold text-orange-400 mb-1.5">⚡ 存在分歧</div>
          {divergencePoints.length > 0 ? (
            <ul className="space-y-1">
              {divergencePoints.map((p, i) => (
                <li key={i} className="text-xs text-orange-300/70 flex gap-1.5">
                  <span className="text-orange-500">·</span> {p}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-slate-500">讨论未产生明显分歧</p>
          )}
        </div>
      </div>

      {/* Summary content */}
      {summaryMsg && (
        <div className="px-6 py-4">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-sm font-semibold text-amber-400">🎤 主持人总结</span>
          </div>
          <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap">
            {summaryMsg.content}
          </p>
        </div>
      )}

      {/* Speaker contributions */}
      <div className="px-6 py-4 border-t border-emerald-500/10">
        <h4 className="text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wide">
          嘉宾贡献统计
        </h4>
        <div className="flex flex-wrap gap-2">
          {Object.entries(speakerCounts).map(([name, count]) => (
            <span
              key={name}
              className="px-3 py-1 rounded-full text-xs bg-slate-700/50 text-slate-300 border border-slate-600/30"
            >
              {name}：{count} 次发言
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

function StatBox({ label, value }: { label: string; value: string }) {
  return (
    <div className="text-center">
      <div className="text-xl font-bold text-emerald-300">{value}</div>
      <div className="text-[10px] text-slate-400 mt-0.5 uppercase tracking-wide">{label}</div>
    </div>
  );
}
