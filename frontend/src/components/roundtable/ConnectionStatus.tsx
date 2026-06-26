import type { DiscussionPhase } from '../../types';

interface ConnectionStatusProps {
  state: 'connecting' | 'open' | 'closed' | 'error' | 'done';
  phase: DiscussionPhase;
  retryCount: number;
  onReconnect: () => void;
}

const phaseLabel: Record<DiscussionPhase, string> = {
  connecting: '连接中...',
  opening: '主持人开场中',
  statements: '嘉宾立场陈述中',
  free_discussion: '自由讨论中',
  summary: '总结中',
  completed: '已完成',
  error: '连接错误',
};

export function ConnectionStatus({ state, phase, retryCount, onReconnect }: ConnectionStatusProps) {
  const isLive = state === 'open' && phase !== 'completed' && phase !== 'error';
  const isError = state === 'error' || phase === 'error';
  const isDone = state === 'done' || phase === 'completed';

  return (
    <div className="flex items-center gap-3">
      <div className="flex items-center gap-2">
        <span
          className={`w-2.5 h-2.5 rounded-full ${
            isLive
              ? 'bg-emerald-400 animate-pulse'
              : isError
              ? 'bg-red-400'
              : isDone
              ? 'bg-emerald-500'
              : 'bg-slate-500'
          }`}
        />
        <span className="text-sm text-slate-400">
          {phaseLabel[phase]}
        </span>
      </div>

      {isError && retryCount >= 3 && (
        <button
          onClick={onReconnect}
          className="px-3 py-1 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-lg text-xs transition-colors"
        >
          重试连接
        </button>
      )}
    </div>
  );
}
