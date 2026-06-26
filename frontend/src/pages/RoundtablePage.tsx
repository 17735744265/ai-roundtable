import { useParams } from 'react-router-dom';
import { RoundtableProvider } from '../store/roundtable-context';
import { RoundtableRoom } from '../components/roundtable/RoundtableRoom';

export default function RoundtablePage() {
  const { id } = useParams<{ id: string }>();

  if (!id) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <p className="text-slate-400">无效的讨论 ID</p>
      </div>
    );
  }

  return (
    <RoundtableProvider>
      <RoundtableRoom sessionId={id} />
    </RoundtableProvider>
  );
}
