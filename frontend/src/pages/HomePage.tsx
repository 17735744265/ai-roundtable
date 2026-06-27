import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchSessions, fetchGuests, generateGuests, createSession, createSessionWithGuests } from '../api/sessions';
import type { SessionBrief, GeneratedGuest } from '../types';

export default function HomePage() {
  const navigate = useNavigate();
  const [activeSessions, setActiveSessions] = useState<SessionBrief[]>([]);
  const [presetGuests, setPresetGuests] = useState<any[]>([]);

  // Flow state
  const [step, setStep] = useState<'input' | 'generating' | 'select' | 'starting'>('input');
  const [topic, setTopic] = useState('');
  const [expertCount, setExpertCount] = useState(4);
  const [showPreset, setShowPreset] = useState(false);
  const [generatedHost, setGeneratedHost] = useState<GeneratedGuest | null>(null);
  const [generatedExperts, setGeneratedExperts] = useState<GeneratedGuest[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchGuests().then(setPresetGuests).catch(() => {});
    fetchSessions(1, 10, 'active')
      .then((d) => setActiveSessions(d.items))
      .catch(() => {});
  }, []);

  // Generate AI lineup
  const handleGenerate = async () => {
    if (!topic.trim()) return;
    setError(null);
    setStep('generating');
    try {
      const result = await generateGuests(topic.trim(), expertCount);
      setGeneratedHost(result.host);
      setGeneratedExperts(result.experts);
      setSelectedIds(new Set(result.experts.map((e: GeneratedGuest) => e.id)));
      setStep('select');
    } catch (e: any) {
      setError(e.message || '生成失败');
      setStep('input');
    }
  };

  const toggleExpert = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const selectedExperts = generatedExperts.filter((e) => selectedIds.has(e.id));
  const canStart = selectedExperts.length >= 3;

  const handleStart = async () => {
    if (!canStart) return;
    setStep('starting');
    setError(null);
    try {
      const session = await createSessionWithGuests(topic.trim(), selectedExperts);
      navigate(`/roundtable/${session.id}`);
    } catch (e: any) {
      setError(e.message || '创建失败');
      setStep('select');
    }
  };

  // Quick start with preset guests
  const [presetSelected, setPresetSelected] = useState<string[]>([]);
  const togglePreset = (id: string) => {
    setPresetSelected((prev) => prev.includes(id) ? prev.filter((g) => g !== id) : [...prev, id]);
  };
  const canPresetStart = topic.trim().length > 0 && presetSelected.length >= 3;

  const handlePresetStart = async () => {
    if (!canPresetStart) return;
    setError(null);
    try {
      const session = await createSession(topic.trim(), presetSelected);
      navigate(`/roundtable/${session.id}`);
    } catch (e: any) {
      setError(e.message || '创建失败');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      <div className="max-w-4xl mx-auto px-4 py-10">
        <div className="text-center mb-10">
          <h1 className="text-4xl font-bold text-white mb-3">🤖 AI 圆桌讨论</h1>
          <p className="text-slate-400">话题 → AI生成专属专家阵容 → 选择嘉宾 → 深度讨论</p>
        </div>

        {/* Active sessions */}
        {activeSessions.length > 0 && (
          <section className="mb-8">
            <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              进行中的讨论
            </h2>
            <div className="space-y-2">
              {activeSessions.map((s) => (
                <button key={s.id} onClick={() => navigate(`/roundtable/${s.id}`)}
                  className="w-full text-left p-3 rounded-xl bg-slate-800/40 border border-slate-700/60
                           hover:border-emerald-500/30 transition-all group">
                  <div className="flex items-center justify-between">
                    <div className="min-w-0">
                      <p className="text-white text-sm font-medium truncate group-hover:text-emerald-300">{s.topic}</p>
                      <div className="flex items-center gap-1.5 mt-1">
                        {s.guests.slice(1, 5).map((g) => (
                          <span key={g.id} className="text-xs px-2 py-0.5 rounded-full bg-slate-700/50 text-slate-300">{g.avatar} {g.name}</span>
                        ))}
                        <span className="text-xs text-slate-500">{s.message_count} 条</span>
                      </div>
                    </div>
                    <span className="text-xs text-emerald-400 flex-shrink-0 ml-3 opacity-0 group-hover:opacity-100">加入 →</span>
                  </div>
                </button>
              ))}
            </div>
          </section>
        )}

        {/* Main: Topic + Generate */}
        <section className="rounded-2xl border border-slate-700/60 bg-slate-800/20 p-6">
          <h2 className="text-lg font-semibold text-white mb-4">🚀 发起新讨论</h2>

          {/* Topic input */}
          <div className="mb-3">
            <textarea value={topic} onChange={(e) => { setTopic(e.target.value); setStep('input'); }}
              placeholder="输入你想探讨的话题，AI将为你生成专属专家阵容..."
              maxLength={200} rows={2}
              className="w-full px-4 py-3 bg-slate-900/60 border border-slate-700 rounded-xl
                       text-white placeholder-slate-500 resize-none
                       focus:outline-none focus:ring-2 focus:ring-blue-500/50 text-sm" />
            <div className="text-right text-xs text-slate-500 mt-1">{topic.length}/200</div>
          </div>

          {/* Expert count + Generate button */}
          <div className="flex items-end gap-3 mb-4">
            <div className="flex-shrink-0">
              <label className="text-xs text-slate-400 mb-1 block">专家人数</label>
              <div className="flex gap-1">
                {[2, 3, 4, 5, 6].map((n) => (
                  <button key={n} onClick={() => setExpertCount(n)}
                    className={`w-8 h-8 rounded-lg text-xs font-medium transition-all ${
                      expertCount === n
                        ? 'bg-blue-500 text-white'
                        : 'bg-slate-700/50 text-slate-400 hover:bg-slate-700'
                    }`}>{n}</button>
                ))}
              </div>
            </div>
            <button onClick={handleGenerate} disabled={!topic.trim() || step === 'generating'}
              className={`flex-1 py-3 rounded-xl text-sm font-semibold transition-all ${
                topic.trim() && step !== 'generating'
                  ? 'bg-gradient-to-r from-blue-500 to-purple-600 text-white hover:shadow-lg active:scale-[0.98]'
                  : 'bg-slate-700 text-slate-500 cursor-not-allowed'
              }`}>
              {step === 'generating' ? '🤖 AI 正在分析话题并生成专家阵容...' : `🤖 AI 生成 ${expertCount} 位专家阵容`}
            </button>
          </div>

          {error && <div className="mb-4 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">{error}</div>}

          {/* Preset guests — collapsed secondary option */}
          <div className="border-t border-slate-700/50 pt-3">
            <button onClick={() => setShowPreset(!showPreset)}
              className="text-xs text-slate-500 hover:text-slate-400 transition-colors">
              {showPreset ? '▲ 收起' : '▼ 或手动选择预设嘉宾（6位固定角色）'}
            </button>
            {showPreset && (
              <div className="mt-3 space-y-2">
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  {presetGuests.map((g: any) => {
                    const sel = presetSelected.includes(g.id);
                    return (
                      <button key={g.id} onClick={() => togglePreset(g.id)}
                        className={`p-2 rounded-xl border text-left transition-all ${
                          sel ? 'border-blue-400 bg-blue-500/10' : 'border-slate-700 bg-slate-800/40 hover:border-slate-600'
                        }`}>
                        <div className="flex items-center gap-1.5">
                          <span className="text-base">{g.avatar}</span>
                          <div>
                            <div className="text-[11px] font-semibold text-white">{g.name}</div>
                            <div className="text-[9px] text-slate-500">{g.description}</div>
                          </div>
                          {sel && <span className="ml-auto text-blue-400 text-xs">✓</span>}
                        </div>
                      </button>
                    );
                  })}
                </div>
                <button onClick={handlePresetStart} disabled={!canPresetStart}
                  className={`w-full py-2 rounded-xl text-xs font-medium transition-all ${
                    canPresetStart ? 'bg-blue-500/20 border border-blue-400/30 text-blue-300 hover:bg-blue-500/30' : 'bg-slate-700/50 text-slate-500 cursor-not-allowed'
                  }`}>
                  直接开始（{presetSelected.length}位预设嘉宾，至少3位）
                </button>
              </div>
            )}
          </div>

          {/* Step: AI Generated → Select experts */}
          {step === 'select' && generatedHost && (
            <div className="space-y-3">
              <div className="p-3 rounded-xl bg-amber-500/8 border border-amber-500/20">
                <div className="flex items-center gap-2">
                  <span className="text-lg">🎤</span>
                  <div>
                    <span className="text-amber-300 font-semibold text-sm">{generatedHost.name}</span>
                    <span className="text-[10px] text-amber-500 ml-2">主持人</span>
                    <p className="text-xs text-slate-400 mt-0.5">{generatedHost.title} · {generatedHost.stance}</p>
                  </div>
                </div>
              </div>

              <p className="text-sm text-slate-400">
                选择专家（已选 {selectedExperts.length} 位，至少 3 位）
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-80 overflow-y-auto">
                {generatedExperts.map((e) => {
                  const sel = selectedIds.has(e.id);
                  return (
                    <button key={e.id} onClick={() => toggleExpert(e.id)}
                      className={`p-3 rounded-xl border-2 text-left transition-all ${
                        sel ? 'border-blue-400 bg-blue-500/10' : 'border-slate-700 bg-slate-800/40 opacity-60 hover:opacity-80'
                      }`}>
                      <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-full flex items-center justify-center text-base flex-shrink-0"
                             style={{ backgroundColor: e.color + '20' }}>{e.avatar}</div>
                        <div className="min-w-0">
                          <div className="flex items-center gap-1.5">
                            <span className="text-white font-semibold text-xs">{e.name}</span>
                            <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ backgroundColor: e.color }} />
                          </div>
                          <p className="text-[10px] text-slate-400">{e.title}</p>
                          <p className="text-[10px] text-slate-500 mt-0.5 line-clamp-1">{e.stance}</p>
                        </div>
                        {sel && <span className="ml-auto text-blue-400 text-sm">✓</span>}
                      </div>
                    </button>
                  );
                })}
              </div>

              <div className="flex gap-3 pt-2">
                <button onClick={() => setStep('input')}
                  className="flex-1 py-2.5 rounded-xl text-sm bg-slate-700 text-slate-300 hover:bg-slate-600 transition-colors">
                  ← 重新生成
                </button>
                <button onClick={handleStart} disabled={!canStart}
                  className={`flex-[2] py-2.5 rounded-xl text-sm font-semibold transition-all ${
                    canStart ? 'bg-gradient-to-r from-blue-500 to-purple-600 text-white hover:shadow-lg active:scale-[0.98]'
                    : 'bg-slate-700 text-slate-500 cursor-not-allowed'
                  }`}>
                  {step === 'starting' ? '⏳ 创建中...' : `✅ 开始讨论（${selectedExperts.length}位专家）`}
                </button>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
