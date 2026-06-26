import type { Message } from '../../types';
import { MessageBubble } from './MessageBubble';

interface PhaseSectionProps {
  title: string;
  phase: string;
  messages: Message[];
}

export function PhaseSection({ title, phase, messages }: PhaseSectionProps) {
  return (
    <div className="rounded-2xl border border-slate-700/60 bg-slate-800/30 overflow-hidden">
      {/* Phase header */}
      <div className="px-5 py-3 bg-slate-800/60 border-b border-slate-700/40">
        <h3 className="text-sm font-semibold text-slate-300">{title}</h3>
      </div>

      {/* Messages */}
      <div className="px-5 py-4 space-y-4">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
      </div>
    </div>
  );
}
