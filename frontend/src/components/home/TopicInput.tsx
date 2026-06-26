interface TopicInputProps {
  value: string;
  onChange: (v: string) => void;
}

export function TopicInput({ value, onChange }: TopicInputProps) {
  return (
    <div className="mb-8">
      <h2 className="text-xl font-semibold text-white mb-4">💬 讨论话题</h2>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="输入你想探讨的话题，例如：远程办公是否应该成为互联网公司的默认工作模式？"
        maxLength={200}
        rows={3}
        className="w-full px-5 py-4 bg-slate-800/60 border border-slate-700 rounded-2xl
                   text-white placeholder-slate-500 resize-none
                   focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50
                   transition-all duration-200"
      />
      <div className="text-right text-xs text-slate-500 mt-1">
        {value.length}/200
      </div>
    </div>
  );
}
