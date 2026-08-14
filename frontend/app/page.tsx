'use client';

import {
  LiveKitRoom,
  RoomAudioRenderer,
  useChat,
  useRoomContext,
  BarVisualizer,
  useTranscriptions,
  DisconnectButton,
} from '@livekit/components-react';
import { useState, useEffect, useRef } from 'react';

interface AnalyticsData {
  total_calls: number;
  successful_calls: number;
  failed_calls: number;
  success_rate: string;
  recent_calls: Array<{ call_id: string; timestamp: string; outcome: string; reason: string }>;
}

function DashboardContent() {
  const { chatMessages } = useChat();
  const room = useRoomContext();
  const transcriptSegments = useTranscriptions();
  const [analytics, setAnalytics] = useState<AnalyticsData>({
    total_calls: 0,
    successful_calls: 0,
    failed_calls: 0,
    success_rate: '0.0',
    recent_calls: [],
  });

  const [sessionTime, setSessionTime] = useState<number>(0);
  const transcriptEndRef = useRef<HTMLDivElement>(null);

  const fetchAnalytics = async () => {
    try {
      const res = await fetch('/api/analytics');
      if (res.ok) {
        const data = await res.json();
        setAnalytics(data);
      }
    } catch (e) {
      // Safe catch to prevent error overlays
    }
  };

  useEffect(() => {
    fetchAnalytics();
    const interval = setInterval(fetchAnalytics, 2000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const timer = setInterval(() => {
      setSessionTime((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Determine active agent name based on remote participant metadata
  const remoteParticipant = Array.from(room.remoteParticipants.values())[0];
  const activeAgent = remoteParticipant?.metadata || remoteParticipant?.name || 'Roshni';
  const isAgentSpeaking = remoteParticipant?.isSpeaking || false;

  const formatDuration = (sec: number) => {
    const mins = Math.floor(sec / 60);
    const secs = sec % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getParticipantName = (identity?: string) => {
    if (!identity) return activeAgent;
    if (identity === room.localParticipant.identity) {
      return 'You';
    }
    const p = Array.from(room.remoteParticipants.values()).find(
      (part) => part.identity === identity
    );
    return p?.name || p?.metadata || activeAgent;
  };

  // Compile transcripts and chat messages into a unified list
  const allMessages = [
    ...transcriptSegments.map((segment) => {
      const isLocal = segment.participantInfo?.identity === room.localParticipant.identity;
      const identity = segment.participantInfo?.identity;
      const senderDisplayName = isLocal ? 'You' : getParticipantName(identity);
      return {
        id: segment.streamInfo.id,
        sender: identity || 'Participant',
        senderDisplayName,
        text: segment.text,
        isLocal,
        timestamp: Date.now(),
      };
    }),
    ...chatMessages.map((c) => {
      const isLocal = c.from?.identity === room.localParticipant.identity;
      const identity = c.from?.identity;
      const senderDisplayName = isLocal ? 'You' : getParticipantName(identity);
      return {
        id: c.timestamp.toString(),
        sender: identity || 'Assistant',
        senderDisplayName,
        text: c.message,
        isLocal,
        timestamp: c.timestamp,
      };
    }),
  ].sort((a, b) => a.timestamp - b.timestamp);

  // Auto-scroll transcript list
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [allMessages.length]);

  return (
    <div className="flex h-screen bg-[#070a13] text-slate-100 font-sans overflow-hidden relative">
      {/* Decorative Deep Space Radial Glows */}
      <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full bg-purple-600/10 blur-[120px] pointer-events-none"></div>
      <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] rounded-full bg-cyan-600/10 blur-[120px] pointer-events-none"></div>

      {/* LEFT COLUMN: Live Transcript Stream */}
      <div className="w-1/3 border-r border-purple-500/10 p-5 flex flex-col bg-slate-950/40 backdrop-blur-xl z-10">
        <div className="flex justify-between items-center mb-4 border-b border-purple-500/10 pb-3">
          <h2 className="text-md font-bold tracking-wide uppercase text-cyan-400 flex items-center gap-2.5">
            <span>💬</span> Live Transcript
          </h2>
          <div className="flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="text-[10px] text-slate-400 font-mono tracking-wider">SYNCED</span>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto space-y-4 pr-2 scrollbar-thin scrollbar-thumb-purple-900/20">
          {allMessages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center px-4">
              <p className="text-slate-500 text-xs italic">
                Speech-to-text transcripts will stream here live when the call starts...
              </p>
            </div>
          ) : (
            allMessages.map((msg, index) => (
              <div
                key={index}
                className={`p-3 rounded-xl max-w-[85%] text-xs transition-all duration-300 ${
                  msg.isLocal
                    ? 'bg-cyan-600/10 border border-cyan-500/20 ml-auto text-cyan-100 shadow-[0_0_10px_rgba(6,182,212,0.05)]'
                    : msg.senderDisplayName === 'Vikram'
                    ? 'bg-purple-950/20 border border-purple-500/20 text-purple-100 shadow-[0_0_10px_rgba(168,85,247,0.05)]'
                    : 'bg-indigo-950/20 border border-indigo-500/20 text-indigo-100 shadow-[0_0_10px_rgba(99,102,241,0.05)]'
                }`}
              >
                <div className="flex items-center gap-1.5 text-[9px] text-slate-400 font-mono mb-1 justify-between">
                  <span>{msg.senderDisplayName}</span>
                  {msg.senderDisplayName !== 'You' && isAgentSpeaking && (
                    <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 animate-pulse"></span>
                  )}
                </div>
                <div className="leading-relaxed whitespace-pre-wrap">{msg.text}</div>
              </div>
            ))
          )}
          <div ref={transcriptEndRef} />
        </div>
      </div>

      {/* CENTER COLUMN: Waveform & Disconnect */}
      <div className="w-1/3 flex flex-col items-center justify-between p-6 z-10">
        {/* Top Branding / Title */}
        <div className="text-center mt-4">
          <div className="inline-block px-3 py-1 rounded-full border border-purple-500/20 bg-purple-950/20 text-[10px] font-bold text-purple-300 uppercase tracking-widest mb-2">
            Roshni AI Financial Hub
          </div>
          <h1 className="text-2xl font-black bg-gradient-to-r from-purple-400 via-indigo-300 to-cyan-400 bg-clip-text text-transparent tracking-tight">
            ACTIVE SESSION
          </h1>
        </div>

        {/* Center Waveform Visualizer & Badge */}
        <div className="w-full flex flex-col items-center justify-center my-auto gap-8">
          {/* Active Agent Badge */}
          <div className="flex flex-col items-center gap-2">
            <span className="text-[10px] font-mono tracking-widest text-slate-500 uppercase">Active Representative</span>
            <div className={`px-5 py-2.5 rounded-full border text-xs font-bold transition-all duration-500 flex items-center gap-2.5 ${
              activeAgent === 'Vikram'
                ? 'bg-purple-950/40 text-purple-300 border-purple-500/30 shadow-[0_0_20px_rgba(168,85,247,0.15)]'
                : 'bg-cyan-950/40 text-cyan-300 border-cyan-500/30 shadow-[0_0_20px_rgba(6,182,212,0.15)]'
            }`}>
              <span className="relative flex h-2 w-2">
                {isAgentSpeaking && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-current opacity-75"></span>}
                <span className={`relative inline-flex rounded-full h-2 w-2 ${isAgentSpeaking ? (activeAgent === 'Vikram' ? 'bg-purple-400' : 'bg-cyan-400') : 'bg-slate-500'}`}></span>
              </span>
              {activeAgent === 'Vikram' ? '👨‍💼 Vikram (Scheme Specialist — Samar)' : '👩‍💼 Roshni (General Banking — Anisha)'}
            </div>
            <span className="text-[9px] font-mono text-slate-400">
              {activeAgent === 'Vikram' ? 'Specialty: Government Subsidies' : 'Specialty: FD & Account Inquiries'}
            </span>
          </div>

          {/* Bar Visualizer */}
          <div className="w-full max-w-[280px] p-6 rounded-2xl bg-slate-900/30 border border-purple-500/10 backdrop-blur-md flex items-center justify-center">
            <BarVisualizer
              state={isAgentSpeaking ? "speaking" : "idle"}
              barCount={7}
              options={{ minHeight: 15 }}
              className={`h-24 w-full transition-colors duration-500 ${activeAgent === 'Vikram' ? 'text-purple-400' : 'text-cyan-400'}`}
            />
          </div>
        </div>

        {/* Action / End Call button */}
        <div className="mb-6 w-full flex flex-col items-center gap-3">
          <DisconnectButton className="px-8 py-3.5 bg-gradient-to-r from-red-600 to-rose-700 hover:from-red-500 hover:to-rose-600 text-white font-bold rounded-xl shadow-[0_0_15px_rgba(220,38,38,0.2)] hover:shadow-[0_0_25px_rgba(220,38,38,0.4)] transition-all duration-300 border border-red-500/30 flex items-center gap-2 cursor-pointer text-xs uppercase tracking-wider">
            <span>🔴</span> End Call / Disconnect
          </DisconnectButton>
          <span className="text-[10px] text-slate-500 font-mono tracking-tight text-center">
            Disconnecting immediately commits and writes session analytics to SQLite.
          </span>
        </div>
      </div>

      {/* RIGHT COLUMN: Live Call Analytics Dashboard */}
      <div className="w-1/3 border-l border-purple-500/10 p-5 flex flex-col bg-slate-950/40 backdrop-blur-xl z-10 overflow-y-auto">
        <h2 className="text-md font-bold tracking-wide uppercase text-purple-400 mb-4 border-b border-purple-500/10 pb-3 flex items-center gap-2">
          <span>📈</span> Analytics Dashboard
        </h2>

        {/* Active Session Tracker */}
        <div className="bg-slate-900/60 border border-purple-500/10 p-3.5 rounded-xl mb-4">
          <div className="text-[10px] font-bold text-slate-400 tracking-wider uppercase mb-2">Active Session Tracker</div>
          <div className="space-y-1.5 font-mono text-xs">
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Connection Status:</span>
              <span className="text-emerald-400 font-bold flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                Connected
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Call Duration:</span>
              <span className="text-cyan-400 font-bold">{formatDuration(sessionTime)}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Active Speaker:</span>
              <span className="text-purple-400 font-bold">{activeAgent}</span>
            </div>
          </div>
        </div>

        {/* Metric Cards Grid */}
        <div className="grid grid-cols-2 gap-3 mb-5">
          <div className="bg-slate-900/40 border border-slate-800 p-3 rounded-xl text-center">
            <span className="text-[9px] text-slate-400 uppercase font-mono tracking-wider">Total Calls</span>
            <div className="text-2xl font-black text-white mt-0.5">{analytics.total_calls}</div>
          </div>
          <div className="bg-slate-900/40 border border-emerald-500/20 p-3 rounded-xl text-center bg-emerald-950/5">
            <span className="text-[9px] text-emerald-400 uppercase font-mono tracking-wider">Successful</span>
            <div className="text-2xl font-black text-emerald-400 mt-0.5">{analytics.successful_calls}</div>
          </div>
          <div className="bg-slate-900/40 border border-rose-500/20 p-3 rounded-xl text-center bg-rose-950/5">
            <span className="text-[9px] text-rose-400 uppercase font-mono tracking-wider">Failed</span>
            <div className="text-2xl font-black text-rose-400 mt-0.5">{analytics.failed_calls}</div>
          </div>
          <div className="bg-slate-900/40 border border-cyan-500/20 p-3 rounded-xl text-center bg-cyan-950/5">
            <span className="text-[9px] text-cyan-400 uppercase font-mono tracking-wider">Success Rate</span>
            <div className="text-2xl font-black text-cyan-300 mt-0.5">{analytics.success_rate}%</div>
          </div>
        </div>

        {/* Recent Call Outcomes Table */}
        <div className="bg-slate-900/40 border border-purple-500/10 p-4 rounded-xl flex-1 flex flex-col min-h-[180px]">
          <span className="text-xs text-slate-300 font-bold tracking-wide block mb-3 uppercase">Recent Call Logs</span>
          {analytics.recent_calls.length === 0 ? (
            <div className="flex-1 flex items-center justify-center">
              <p className="text-slate-500 text-xs italic">No historical outcomes logged.</p>
            </div>
          ) : (
            <div className="space-y-2 flex-1 overflow-y-auto max-h-[220px]">
              {analytics.recent_calls.map((call, idx) => (
                <div key={idx} className="p-2.5 bg-slate-950/40 rounded-lg border border-slate-900 text-xs flex justify-between items-center gap-3">
                  <div className="min-w-0">
                    <div className="font-mono text-[9px] text-slate-500">{call.call_id}</div>
                    <div className="text-slate-300 mt-0.5 truncate text-[11px]" title={call.reason}>{call.reason}</div>
                  </div>
                  <span className={`px-2 py-0.5 text-[9px] font-mono font-bold rounded flex-shrink-0 ${
                    call.outcome === 'SUCCESS' 
                      ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' 
                      : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                  }`}>
                    {call.outcome}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function Home() {
  const [token, setToken] = useState<string>('');
  const [url, setUrl] = useState<string>('');
  const [particles, setParticles] = useState<Array<{ id: number; symbol: string; left: string; top: string; size: string; delay: string; duration: string }>>([]);

  const connectToRoom = async () => {
    try {
      const res = await fetch('/api/token');
      if (!res.ok) {
        console.error('Token fetch failed');
        return;
      }
      const data = await res.json();
      setToken(data.token);
      setUrl(data.url);
    } catch (e) {
      console.error('Connection error:', e);
    }
  };

  // Generate floating background particles once on load
  useEffect(() => {
    const symbols = ['₹', '$', '%', '🏛️', '📈', '🛡️'];
    const newParticles = Array.from({ length: 18 }).map((_, i) => ({
      id: i,
      symbol: symbols[Math.floor(Math.random() * symbols.length)],
      left: `${Math.random() * 100}%`,
      top: `${Math.random() * 85 + 5}%`,
      size: `${Math.random() * 14 + 10}px`,
      delay: `${Math.random() * -10}s`, // Negative delay to start mid-animation
      duration: `${Math.random() * 12 + 12}s`,
    }));
    setParticles(newParticles);
  }, []);

  return (
    <main className="h-screen w-screen bg-[#070a13] relative overflow-hidden flex flex-col justify-between">
      {/* Background radial overlays */}
      <div className="absolute top-[-20%] left-[-20%] w-[60%] h-[60%] rounded-full bg-purple-600/5 blur-[150px] pointer-events-none"></div>
      <div className="absolute bottom-[-20%] right-[-20%] w-[60%] h-[60%] rounded-full bg-cyan-600/5 blur-[150px] pointer-events-none"></div>

      {/* Floating particles background (Landing page only) */}
      {!token && particles.map((p) => (
        <div
          key={p.id}
          className="absolute pointer-events-none text-purple-500/10 select-none animate-float z-0"
          style={{
            left: p.left,
            top: p.top,
            fontSize: p.size,
            animationDelay: p.delay,
            animationDuration: p.duration,
          }}
        >
          {p.symbol}
        </div>
      ))}

      {!token ? (
        <div className="flex-1 flex flex-col items-center justify-center px-4 relative z-10">
          {/* Header & Logo */}
          <div className="text-center mb-8 max-w-2xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-purple-500/20 bg-purple-950/20 text-purple-300 text-[10px] font-extrabold uppercase tracking-widest mb-4 shadow-[0_0_10px_rgba(168,85,247,0.1)]">
              🚀 ROSHNI AI — YOUR FINANCIAL VOICE ASSISTANT
            </div>
            <h1 className="text-4xl sm:text-5xl font-black bg-gradient-to-r from-purple-400 via-indigo-300 to-cyan-400 bg-clip-text text-transparent tracking-tight leading-none mb-3">
              Future of Voice Banking
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 leading-relaxed max-w-md mx-auto">
              Real-time multi-agent fintech portal powered by LiveKit & Murf Falcon TTS. Conversational, secure, and smart.
            </p>

            {/* Language Badges */}
            <div className="flex justify-center items-center gap-2 mt-4">
              <span className="text-[10px] font-mono tracking-widest text-slate-500 uppercase mr-1">Languages:</span>
              <span className="px-2.5 py-0.5 rounded bg-slate-900 border border-slate-800 text-[10px] text-slate-300 font-medium">English</span>
              <span className="px-2.5 py-0.5 rounded bg-slate-900 border border-slate-800 text-[10px] text-slate-300 font-medium font-hindi">हिन्दी (Devanagari)</span>
              <span className="px-2.5 py-0.5 rounded bg-slate-900 border border-slate-800 text-[10px] text-slate-300 font-medium">Hinglish</span>
            </div>
          </div>

          {/* 2x2 Domain Cards Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-2xl w-full mb-10">
            {/* Card 1: Banking & Interest Rates */}
            <div className="p-4 bg-slate-950/40 border border-purple-500/10 rounded-2xl backdrop-blur-md hover:border-cyan-500/30 hover:-translate-y-1 transition-all duration-300 shadow-[0_4px_20px_rgba(0,0,0,0.4)] flex gap-3">
              <div className="text-2xl">🏛️</div>
              <div>
                <h3 className="text-xs font-black text-cyan-400 uppercase tracking-wider mb-1">Banking & Interest Rates</h3>
                <p className="text-[11px] text-slate-400 leading-normal">
                  Live FD, Senior Citizen schemes, and Savings rate lookups. Powered by <code className="font-mono text-purple-300 bg-slate-900/60 px-1 py-0.5 rounded">check_scheme_rates</code>.
                </p>
              </div>
            </div>

            {/* Card 2: Government Schemes */}
            <div className="p-4 bg-slate-950/40 border border-purple-500/10 rounded-2xl backdrop-blur-md hover:border-cyan-500/30 hover:-translate-y-1 transition-all duration-300 shadow-[0_4px_20px_rgba(0,0,0,0.4)] flex gap-3">
              <div className="text-2xl">📜</div>
              <div>
                <h3 className="text-xs font-black text-cyan-400 uppercase tracking-wider mb-1">Subsidies & Schemes</h3>
                <p className="text-[11px] text-slate-400 leading-normal">
                  Interact with our dedicated government specialist agent, <span className="text-purple-300 font-semibold">Vikram</span>, for welfare inquiries.
                </p>
              </div>
            </div>

            {/* Card 3: Fraud Safety & Escalation */}
            <div className="p-4 bg-slate-950/40 border border-purple-500/10 rounded-2xl backdrop-blur-md hover:border-cyan-500/30 hover:-translate-y-1 transition-all duration-300 shadow-[0_4px_20px_rgba(0,0,0,0.4)] flex gap-3">
              <div className="text-2xl">🛡️</div>
              <div>
                <h3 className="text-xs font-black text-cyan-400 uppercase tracking-wider mb-1">Fraud & Human Escalation</h3>
                <p className="text-[11px] text-slate-400 leading-normal">
                  Instant human hand-off generating <code className="font-mono text-purple-300 bg-slate-900/60 px-1 py-0.5 rounded">REF-FIN-XXXX</code> ticket dispatch.
                </p>
              </div>
            </div>

            {/* Card 4: Outbound Deadlines & Alerts */}
            <div className="p-4 bg-slate-950/40 border border-purple-500/10 rounded-2xl backdrop-blur-md hover:border-cyan-500/30 hover:-translate-y-1 transition-all duration-300 shadow-[0_4px_20px_rgba(0,0,0,0.4)] flex gap-3">
              <div className="text-2xl">📞</div>
              <div>
                <h3 className="text-xs font-black text-cyan-400 uppercase tracking-wider mb-1">Deadlines & Opt-Out</h3>
                <p className="text-[11px] text-slate-400 leading-normal">
                  Automated rate maturity reminders. Supports immediate notification opt-out detection.
                </p>
              </div>
            </div>
          </div>

          {/* Action Start Button */}
          <button
            onClick={connectToRoom}
            className="px-10 py-4 bg-gradient-to-r from-purple-600 via-indigo-600 to-cyan-500 rounded-2xl font-bold uppercase tracking-wider text-xs shadow-[0_0_15px_rgba(168,85,247,0.3)] hover:shadow-[0_0_25px_rgba(6,182,212,0.5)] hover:scale-[1.03] transition-all duration-300 cursor-pointer text-white glow-btn-purple"
          >
            🎙️ START ROSHNI AI
          </button>
        </div>
      ) : (
        <LiveKitRoom
          serverUrl={url}
          token={token}
          connect={true}
          audio={true}
          video={false}
          onDisconnected={() => {
            setToken('');
            setUrl('');
          }}
        >
          <DashboardContent />
          <RoomAudioRenderer />
        </LiveKitRoom>
      )}

      {/* Subtle Footer */}
      {!token && (
        <div className="py-4 text-center border-t border-purple-500/5 bg-slate-950/20 backdrop-blur-sm z-10 text-[9px] text-slate-500 font-mono uppercase tracking-widest">
          ROSHNI FINTECH GATEWAY • POWERED BY DEEPMIND & LIVEKIT
        </div>
      )}
    </main>
  );
}