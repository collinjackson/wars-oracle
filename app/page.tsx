'use client';

import { useState, useEffect, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { useChat } from '@ai-sdk/react';
import { Send, Map as MapIcon, ShieldAlert, Coins, RefreshCw, Share2 } from 'lucide-react';
import { clsx } from 'clsx';

function HomeContent() {
  const APP_VERSION = '0.0.1';
  const searchParams = useSearchParams();
  const [gameId, setGameId] = useState('');
  const [username, setUsername] = useState('');
  const [analysis, setAnalysis] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [players, setPlayers] = useState<any[]>([]);
  const [isGameLoaded, setIsGameLoaded] = useState(false);
  const [copied, setCopied] = useState(false);

  // Initialize from URL params
  useEffect(() => {
    const urlGameId = searchParams.get('game_id') || searchParams.get('id');
    const urlUsername = searchParams.get('username');

    if (urlGameId) {
      setGameId(urlGameId);
      // Auto-load if ID exists
      loadPlayers(urlGameId).then((success) => {
        if (success && urlUsername) {
          setUsername(urlUsername);
          fetchAnalysis(urlGameId, urlUsername);
        }
      });
    }
  }, []);

  const { messages, input, handleInputChange, handleSubmit, setMessages, isLoading } = useChat({
    api: '/api/chat',
    body: {
      data: {
        analysis,
        username
      }
    }
  });

  const loadPlayers = async (overrideId?: string) => {
    const targetIdRaw = overrideId || gameId;
    if (!targetIdRaw) return false;
    
    setLoading(true);
    setError('');
    // Only reset state if manually clicking load, not initial hydration
    if (!overrideId) {
      setAnalysis(null);
      setMessages([]);
      setPlayers([]);
      setUsername('');
      setIsGameLoaded(false);
    }

    let targetId = targetIdRaw.trim();
    const urlMatch = targetId.match(/games_id=(\d+)/);
    if (urlMatch) {
      targetId = urlMatch[1];
      setGameId(targetId);
    }

    try {
      const res = await fetch(`/api/game/${targetId}/players`);
      if (!res.ok) throw new Error('Failed to load players');
      const data = await res.json();
      setPlayers(data);
      setIsGameLoaded(true);
      return true;
    } catch (err: any) {
      setError(err.message);
      return false;
    } finally {
      setLoading(false);
    }
  };

  const handlePlayerSelect = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const user = e.target.value;
    setUsername(user);
    if (user) {
        fetchAnalysis(undefined, user);
    } else {
        setAnalysis(null);
        setMessages([]);
    }
  };

  const fetchAnalysis = async (overrideId?: string, targetUsername?: string) => {
    const userToFetch = targetUsername || username;
    const idToFetch = overrideId || gameId;
    
    if (!idToFetch || !userToFetch) return;
    setLoading(true);
    setError('');
    
    let targetId = idToFetch.trim();
    const urlMatch = targetId.match(/games_id=(\d+)/);
    if (urlMatch) {
      targetId = urlMatch[1];
    }

    try {
      let url = `/api/game/${targetId}/analysis?username=${userToFetch}`;
      
      const res = await fetch(url);
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.error || 'Failed to fetch analysis');
      }
      
      const data = await res.json();
      setAnalysis(data);
      
      // Reset chat with a system welcome message based on analysis
      setMessages([
        {
          id: 'welcome',
          role: 'assistant',
          content: `I've analyzed game ${targetId} for ${userToFetch}. \n\nI see ${data.threats?.length || 0} immediate threats and you have ${data.economy?.[Object.keys(data.economy)[0]]?.funds || 0}G in funds. What would you like to know?`
        }
      ]);
      
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleShare = () => {
    if (!window) return;
    const url = new URL(window.location.href);
    url.searchParams.set('game_id', gameId);
    if (username) url.searchParams.set('username', username);
    
    navigator.clipboard.writeText(url.toString());
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <main className="min-h-screen bg-gray-900 text-gray-100 flex flex-col">
      <header className="bg-gray-800 border-b border-gray-700 p-4">
        <div className="container mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-2xl">🔮</span>
            <h1 className="text-xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
              Wars Oracle
            </h1>
            <span className="bg-blue-900/50 text-blue-300 text-xs px-2 py-0.5 rounded border border-blue-800 font-semibold tracking-wide">BETA</span>
          </div>
          {analysis && (
            <button 
              onClick={handleShare}
              className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition bg-gray-700/50 px-3 py-1.5 rounded-lg border border-gray-600 hover:border-gray-500"
            >
              <Share2 className="w-4 h-4" />
              {copied ? 'Copied Link!' : 'Share Analysis'}
            </button>
          )}
        </div>
      </header>

      <div className="flex-1 container mx-auto p-4 flex flex-col lg:flex-row gap-6 overflow-hidden">
        
        {/* Left Panel: Controls & Analysis */}
        <div className="w-full lg:w-1/3 flex flex-col gap-6 overflow-y-auto">
          
          {/* Controls */}
          <div className="bg-gray-800 rounded-xl p-4 border border-gray-700 space-y-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Game Link or ID</label>
              <div className="flex gap-2">
                <input 
                  type="text" 
                  value={gameId}
                  onChange={(e) => setGameId(e.target.value)}
                  placeholder="https://awbw.amarriner.com/game.php?games_id=123456"
                  className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 outline-none text-sm"
                />
                <button 
                  onClick={() => loadPlayers()}
                  disabled={loading}
                  className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-4 py-2 rounded-lg font-medium transition"
                >
                  Load
                </button>
              </div>
            </div>

            {isGameLoaded && (
              <div>
                <label className="block text-sm text-gray-400 mb-1">Select Player</label>
                <select 
                  value={username}
                  onChange={handlePlayerSelect}
                  className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 outline-none appearance-none"
                >
                  <option value="">-- Select a Player --</option>
                  {players.map((p: any) => (
                    <option key={p.id} value={p.username}>
                      {p.username} ({p.co}) - {p.team}
                    </option>
                  ))}
                </select>
              </div>
            )}
            
            {loading && <div className="text-center text-blue-400 text-sm animate-pulse">Analyzing battlefield strategy...</div>}

            {error && <p className="text-red-400 text-sm mt-2">{error}</p>}
          </div>

          {/* Analysis View */}
          {analysis && (
            <div className="space-y-4">
              {/* Economy Card */}
              <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
                <h3 className="flex items-center gap-2 text-lg font-semibold mb-3 text-yellow-400">
                  <Coins className="w-5 h-5" /> Economy
                </h3>
                <div className="space-y-3">
                  {Object.entries(analysis.economy || {}).map(([slot, stats]: [string, any]) => (
                     <div key={slot} className={clsx("p-2 rounded bg-gray-900 border border-gray-700", stats.username.toLowerCase() === username.toLowerCase() ? "border-yellow-500/50" : "")}>
                       <div className="flex justify-between items-center mb-1">
                         <span className="font-bold text-gray-200">{stats.username}</span>
                         <span className="text-xs text-gray-400">({stats.co})</span>
                       </div>
                       <div className="grid grid-cols-2 gap-2 text-sm">
                         <div className="text-green-400">💰 {stats.income}</div>
                         <div className="text-blue-400">🛠 {stats.unit_count} Units</div>
                         <div className="text-gray-400 col-span-2">Val: {stats.unit_value}</div>
                       </div>
                     </div>
                  ))}
                </div>
              </div>

              {/* Strategic Advice Card */}
              {analysis.advice && analysis.advice.length > 0 && (
                <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
                  <h3 className="flex items-center gap-2 text-lg font-semibold mb-3 text-blue-400">
                    <ShieldAlert className="w-5 h-5" /> Strategic Advice
                  </h3>
                  <ul className="space-y-2">
                    {analysis.advice.map((tip: string, idx: number) => (
                      <li key={idx} className="bg-blue-900/30 p-2 rounded border border-blue-800/50 text-sm text-blue-200">
                        {tip}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Threats Card (Collapsed/Secondary) */}
              <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
                <h3 className="flex items-center gap-2 text-lg font-semibold mb-3 text-red-400">
                  <ShieldAlert className="w-5 h-5" /> Threat Detail
                </h3>
                {analysis.threats && analysis.threats.length > 0 ? (
                  <ul className="space-y-2 max-h-60 overflow-y-auto pr-1">
                    {analysis.threats.slice(0, 10).map((threat: any, idx: number) => (
                      <li key={idx} className="bg-gray-900/50 p-2 rounded border border-red-900/30 text-sm">
                        <div className="flex justify-between text-red-200">
                          <span>⚠️ <b>{threat.attacker.type}</b></span>
                          <span className="text-red-400">-{threat.damage_pct}%</span>
                        </div>
                        <div className="text-xs text-gray-500 mt-1">
                          vs {threat.victim.type} at ({threat.victim.pos[0]},{threat.victim.pos[1]})
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-gray-500 italic">No immediate threats detected.</p>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Right Panel: Chat */}
        <div className="flex-1 bg-gray-800 rounded-xl border border-gray-700 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.length === 0 && !analysis && (
              <div className="h-full flex flex-col items-center justify-center text-gray-500 opacity-50">
                <span className="text-6xl mb-4">💬</span>
                <p>Enter a Game ID to start strategizing.</p>
              </div>
            )}
            
            {messages.map(m => (
              <div key={m.id} className={clsx(
                "flex w-full",
                m.role === 'user' ? "justify-end" : "justify-start"
              )}>
                <div className={clsx(
                  "max-w-[85%] rounded-2xl px-4 py-3",
                  m.role === 'user' 
                    ? "bg-blue-600 text-white rounded-tr-none" 
                    : "bg-gray-700 text-gray-100 rounded-tl-none"
                )}>
                  <p className="whitespace-pre-wrap leading-relaxed">{m.content}</p>
                </div>
              </div>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="p-4 bg-gray-900 border-t border-gray-700 flex gap-2">
            <input
              className="flex-1 bg-gray-800 text-white rounded-lg px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500 border border-gray-700"
              value={input || ''}
              onChange={handleInputChange}
              placeholder={analysis ? "Ask about strategy..." : "Load a game first..."}
              disabled={!analysis}
            />
            <button 
              type="submit"
              disabled={!analysis || !input?.trim() || isLoading}
              className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white px-6 rounded-lg transition flex items-center"
            >
              {isLoading ? <RefreshCw className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
            </button>
          </form>
        </div>

      </div>
      <footer className="p-4 border-t border-gray-800 text-center text-gray-600 text-xs">
        <p>Wars Oracle Engine v{APP_VERSION} &bull; Not affiliated with Advance Wars or Nintendo.</p>
      </footer>
    </main>
  );
}

export default function Home() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-gray-900 text-white flex items-center justify-center">Loading Oracle...</div>}>
      <HomeContent />
    </Suspense>
  );
}
