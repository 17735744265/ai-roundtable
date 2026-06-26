import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { fetchSession } from '../api/sessions';
import type { SessionDetail, Message } from '../types';
import { PhaseSection } from '../components/roundtable/PhaseSection';

export default function HistoryDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [session, setSession] = useState<SessionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    fetchSession(id)
      .then(setSession)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <p className="text-slate-400">加载讨论记录...</p>
      </div>
    );
  }

  if (error || !session) {
    return (
      <div className="min-h-screen bg-slate-900 flex flex-col items-center justify-center gap-4">
        <p className="text-red-400">{error || '讨论不存在'}</p>
        <Link to="/history" className="text-blue-400 hover:text-blue-300 text-sm">
          ← 返回历史记录
        </Link>
      </div>
    );
  }

  const phaseMessages = {
    opening: session.messages.filter((m: Message) => m.phase === 'opening'),
    statements: session.messages.filter((m: Message) => m.phase === 'statements'),
    free_discussion: session.messages.filter((m: Message) => m.phase === 'free_discussion'),
    summary: session.messages.filter((m: Message) => m.phase === 'summary'),
  };

  const phaseLabel: Record<string, string> = {
    opening: '第一阶段 · 主持人开场',
    statements: '第二阶段 · 嘉宾立场陈述',
    free_discussion: '第三阶段 · 自由讨论',
    summary: '第四阶段 · 主持人总结',
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <div className="max-w-4xl mx-auto px-4 py-12">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <Link to="/history" className="text-sm text-blue-400 hover:text-blue-300 mb-2 inline-block">
              ← 返回历史记录
            </Link>
            <h1 className="text-2xl font-bold text-white">📋 {session.topic}</h1>
            <div className="flex items-center gap-2 mt-2">
              {session.guests.map((g) => (
                <span key={g.id} className="text-sm text-slate-400">
                  {g.avatar} {g.name}
                </span>
              ))}
            </div>
          </div>
          <div className="text-right text-sm text-slate-500">
            <p>{new Date(session.created_at).toLocaleString('zh-CN')}</p>
            <p>共 {session.messages.length} 条发言</p>
          </div>
        </div>

        {/* Messages */}
        <div className="space-y-8">
          {Object.entries(phaseMessages).map(([phase, messages]) =>
            messages.length > 0 ? (
              <PhaseSection
                key={phase}
                title={phaseLabel[phase]}
                phase={phase}
                messages={messages}
              />
            ) : null
          )}
        </div>
      </div>
    </div>
  );
}
