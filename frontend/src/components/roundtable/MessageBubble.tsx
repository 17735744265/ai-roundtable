import type { Message } from '../../types';

interface MessageBubbleProps {
  message: Message;
  isSpeaking: boolean;
  isNew: boolean;
  guestTitle: string;
  guestColor: string;
}

export function MessageBubble({ message, isSpeaking, isNew, guestTitle, guestColor }: MessageBubbleProps) {
  const isModerator = message.speaker_id === 'moderator';
  const color = guestColor || '#94A3B8';

  return (
    <div className={`flex gap-3 ${isNew ? 'message-enter' : ''}`}>
      {/* Avatar */}
      <div className="flex-shrink-0 pt-0.5">
        <div
          className={`w-8 h-8 rounded-full flex items-center justify-center text-base
            ${isModerator
              ? 'bg-amber-500/15 ring-1 ring-amber-400/30'
              : 'bg-slate-700/50'}
            ${isSpeaking ? (isModerator ? 'avatar-breathing-moderator' : 'avatar-breathing') : ''}
          `}
          style={!isModerator ? { borderColor: color + '40' } : {}}
        >
          {isModerator ? '🎤' : '💬'}
        </div>
      </div>

      {/* Content */}
      <div
        className={`flex-1 min-w-0 rounded-xl px-3.5 py-2.5 border
          ${isModerator
            ? 'bg-amber-500/5 border-amber-500/20 border-l-2 border-l-amber-400'
            : 'bg-slate-800/30 border-slate-700/40'}`}
        style={!isModerator ? { borderLeftColor: color, borderLeftWidth: '2px' } : {}}
      >
        {/* Name + Title */}
        <div className="flex items-center gap-2 mb-1">
          <span className={`text-xs font-semibold ${isModerator ? 'text-amber-400' : 'text-slate-200'}`}>
            {message.speaker_name}
          </span>
          {guestTitle && (
            <span className="text-[10px] text-slate-500 truncate">{guestTitle}</span>
          )}
          {isModerator && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-400">主持人</span>
          )}
        </div>

        {/* Text */}
        <p className="text-xs text-slate-300 leading-relaxed whitespace-pre-wrap">
          {message.content}
        </p>
      </div>
    </div>
  );
}
