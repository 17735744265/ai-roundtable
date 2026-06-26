import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import HomePage from './pages/HomePage';
import RoundtablePage from './pages/RoundtablePage';
import HistoryPage from './pages/HistoryPage';
import HistoryDetailPage from './pages/HistoryDetailPage';

function Navbar() {
  const location = useLocation();
  const isHome = location.pathname === '/';

  return (
    <nav className="sticky top-0 z-50 bg-slate-900/80 backdrop-blur-md border-b border-slate-700/40">
      <div className="max-w-4xl mx-auto px-4 h-14 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2 text-white font-bold text-lg">
          🤖 AI Roundtable
        </Link>
        <div className="flex items-center gap-4">
          {!isHome && (
            <Link
              to="/"
              className="text-sm text-slate-400 hover:text-white transition-colors"
            >
              新建讨论
            </Link>
          )}
          <Link
            to="/history"
            className="text-sm text-slate-400 hover:text-white transition-colors"
          >
            历史记录
          </Link>
        </div>
      </div>
    </nav>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Navbar />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/roundtable/:id" element={<RoundtablePage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/history/:id" element={<HistoryDetailPage />} />
      </Routes>
    </BrowserRouter>
  );
}
