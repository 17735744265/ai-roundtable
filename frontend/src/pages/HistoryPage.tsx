import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { fetchSessions, deleteSession } from '../api/sessions';
import type { SessionBrief } from '../types';

export default function HistoryPage() {
  const [sessions, setSessions] = useState<SessionBrief[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadSessions = async (p: number) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchSessions(p);
      setSessions(data.items);
      setTotal(data.total);
    } catch (e: any) {
      setError(e.message || '加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSessions(page);
  }, [page]);

  const handleDelete = async (id: string) => {
    if (!window.confirm('确定删除这个讨论记录吗？')) return;
    try {
      await deleteSession(id);
      loadSessions(page);
    } catch (e: any) {
      setError(e.message || '删除失败');
    }
  };

  const statusBadge = (status: string) => {
    const map: Record<string, { label: string; cls: string }> = {
      active: { label: '进行中', cls: 'bg-blue-500/10 text-blue-400 border-blue-500/20' },
      completed: { label: '已完成', cls: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' },
      error: { label: '异常', cls: 'bg-red-500/10 text-red-400 border-red-500/20' },
    };
    const s = map[status] || { label: status, cls: 'bg-slate-500/10 text-slate-400' };
    return (
      <span className={`px-2 py-0.5 rounded-full text-xs border ${s.cls}`}>
        {s.label}
      </span>
    );
  };

  const totalPages = Math.ceil(total / 20);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <div className="max-w-4xl mx-auto px-4 py-12">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-white">📋 历史记录</h1>
            <p className="text-slate-400 mt-1">共 {total} 场讨论</p>
          </div>
          <Link
            to="/"
            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-xl text-sm transition-colors"
          >
            + 新建讨论
          </Link>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-sm">
            {error}
          </div>
        )}

        {loading ? (
          <div className="text-center py-20 text-slate-400">加载中...</div>
        ) : sessions.length === 0 ? (
          <div className="text-center py-20">
            <p className="text-5xl mb-4">📭</p>
            <p className="text-slate-400">暂无讨论记录</p>
            <Link to="/" className="text-blue-400 hover:text-blue-300 text-sm mt-2 inline-block">
              开始第一场讨论 →
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {sessions.map((s) => (
              <div
                key={s.id}
                className="flex items-center justify-between p-5 bg-slate-800/40 border border-slate-700/60 rounded-2xl hover:border-slate-600/80 transition-colors"
              >
                <Link to={`/history/${s.id}`} className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    {statusBadge(s.status)}
                    <span className="text-xs text-slate-500">{s.message_count} 条发言</span>
                  </div>
                  <p className="text-white font-medium truncate">{s.topic}</p>
                  <div className="flex items-center gap-2 mt-1">
                    {s.guests.map((g) => (
                      <span key={g.id} className="text-sm" title={g.name}>
                        {g.avatar}
                      </span>
                    ))}
                    <span className="text-xs text-slate-500">
                      {new Date(s.created_at).toLocaleString('zh-CN')}
                    </span>
                  </div>
                </Link>
                <button
                  onClick={(e) => {
                    e.preventDefault();
                    handleDelete(s.id);
                  }}
                  className="ml-4 px-3 py-1 text-xs text-slate-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                >
                  删除
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex justify-center gap-2 mt-8">
            {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
              <button
                key={p}
                onClick={() => setPage(p)}
                className={`w-10 h-10 rounded-xl text-sm font-medium transition-colors ${
                  p === page
                    ? 'bg-blue-500 text-white'
                    : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                }`}
              >
                {p}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
