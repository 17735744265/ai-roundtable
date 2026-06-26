import type { Guest } from '../../types';

interface GuestSelectorProps {
  guests: Guest[];
  selectedIds: string[];
  onToggle: (id: string) => void;
}

export function GuestSelector({ guests, selectedIds, onToggle }: GuestSelectorProps) {
  return (
    <div className="grid grid-cols-3 gap-3">
      {guests.map((guest) => {
        const isSelected = selectedIds.includes(guest.id);
        const isDisabled = !isSelected && selectedIds.length >= 3;

        return (
          <button
            key={guest.id}
            onClick={() => !isDisabled && onToggle(guest.id)}
            disabled={isDisabled}
            className={`relative p-4 rounded-2xl border-2 text-left transition-all duration-200 ${
              isSelected
                ? 'border-blue-400 bg-blue-500/10 shadow-lg shadow-blue-500/10'
                : isDisabled
                ? 'border-slate-700 bg-slate-800/30 opacity-40 cursor-not-allowed'
                : 'border-slate-700 bg-slate-800/40 hover:border-slate-600 hover:bg-slate-800/60 cursor-pointer'
            }`}
          >
            {/* Checkbox indicator */}
            <div className="absolute top-2 right-2">
              <div
                className={`w-5 h-5 rounded-full border-2 flex items-center justify-center transition-all ${
                  isSelected
                    ? 'border-blue-400 bg-blue-500'
                    : 'border-slate-600 bg-transparent'
                }`}
              >
                {isSelected && <span className="text-white text-xs">✓</span>}
              </div>
            </div>

            <div className="text-3xl mb-2">{guest.avatar}</div>
            <div className="text-sm font-semibold text-white mb-1">{guest.name}</div>
            <div className="text-xs text-slate-400 leading-relaxed">{guest.description}</div>
          </button>
        );
      })}
    </div>
  );
}
