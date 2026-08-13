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
import { useState, useEffect } from 'react';

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

  const allMessages = [
    ...transcriptSegments.map((segment) => ({
      id: segment.streamInfo.id,
      sender: segment.participantInfo?.identity || 'Participant',
      text: segment.text,
    })),
    ...chatMessages.map((c) => ({
      id: c.timestamp.toString(),
      sender: c.from?.identity || 'Roshni AI',
      text: c.message,
    })),
  ];

  return (
    <div className="flex h-screen bg-slate-950 text-white font-sans overflow-hidden">
      {/* LEFT COLUMN: Live Transcript */}
      <div className="w-1/3 border-r border-slate-800 p-4 flex flex-col bg-slate-900/50">
        <h2 className="text-lg font-bold text-cyan-400 mb-3 flex items-center gap-2">
          <span>💬</span> Live Transcript
        </h2>
        <div className="flex-1 overflow-y-auto space-y-3 pr-2 scrollbar-thin">
          {allMessages.length === 0 ? (
            <p className="text-slate-500 text-sm italic">
              Transcripts will stream here live when the call starts...
            </p>
          ) : (
            allMessages.map((msg, index) => (
              <div
                key={index}
                className={`p-3 rounded-xl max-w-[90%] text-sm ${
                  msg.sender === room.localParticipant.identity
                    ? 'bg-cyan-600/30 border border-cyan-500/40 ml-auto text-right text-cyan-100'
                    : 'bg-slate-800 border border-slate-700 text-slate-200'
                }`}
              >
                <div className="text-[10px] text-slate-400 font-mono mb-1">
                  {msg.sender === room.localParticipant.identity ? 'You' : 'Roshni AI'}
                </div>
                <div>{msg.text}</div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* CENTER COLUMN: Audio Visualizer & Explicit End Call Controls */}
      <div className="w-1/3 flex flex-col items-center justify-between p-6 bg-slate-950">
        <div className="text-center mt-4">
          <h1 className="text-2xl font-bold bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">
            Roshni AI
          </h1>
          <p className="text-xs text-slate-400 mt-1">Financial Services Assistant • Murf Falcon Powered</p>
        </div>

        <div className="w-full flex flex-col items-center justify-center my-auto">
          <BarVisualizer
            state="speaking"
            barCount={7}
            options={{ minHeight: 20 }}
            className="h-32 w-full text-cyan-400"
          />
        </div>

        {/* Explicit Disconnect / End Call Button */}
        <div className="mb-6 w-full flex flex-col items-center gap-3">
          <DisconnectButton className="px-6 py-3 bg-rose-600 hover:bg-rose-700 text-white font-bold rounded-xl shadow-lg transition duration-200 border border-rose-500/40 flex items-center gap-2">
            <span>🔴</span> End Call / Disconnect
          </DisconnectButton>
          <span className="text-[11px] text-slate-500">
            Clicking End Call closes session & triggers outcome save to SQLite
          </span>
        </div>
      </div>

      {/* RIGHT COLUMN: Real-Time Call Analytics Dashboard */}
      <div className="w-1/3 border-l border-slate-800 p-4 flex flex-col bg-slate-900/50 overflow-y-auto">
        <h2 className="text-lg font-bold text-emerald-400 mb-3 flex items-center gap-2">
          <span>📈</span> Call Analytics Dashboard
        </h2>
        
        {/* Metric Cards */}
        <div className="grid grid-cols-2 gap-3 mb-4">
          <div className="bg-slate-800/80 border border-slate-700 p-3 rounded-xl text-center">
            <span className="text-[10px] text-slate-400 uppercase font-semibold">Total Calls</span>
            <div className="text-2xl font-extrabold text-white mt-1">{analytics.total_calls}</div>
          </div>
          <div className="bg-slate-800/80 border border-emerald-500/30 p-3 rounded-xl text-center bg-emerald-950/10">
            <span className="text-[10px] text-emerald-400 uppercase font-semibold">Successful Calls</span>
            <div className="text-2xl font-extrabold text-emerald-400 mt-1">{analytics.successful_calls}</div>
          </div>
          <div className="bg-slate-800/80 border border-rose-500/30 p-3 rounded-xl text-center bg-rose-950/10">
            <span className="text-[10px] text-rose-400 uppercase font-semibold">Failed Calls</span>
            <div className="text-2xl font-extrabold text-rose-400 mt-1">{analytics.failed_calls}</div>
          </div>
          <div className="bg-slate-800/80 border border-cyan-500/30 p-3 rounded-xl text-center bg-cyan-950/10">
            <span className="text-[10px] text-cyan-400 uppercase font-semibold">Success Rate</span>
            <div className="text-2xl font-extrabold text-cyan-300 mt-1">{analytics.success_rate}%</div>
          </div>
        </div>

        {/* Recent Call Outcomes Table */}
        <div className="bg-slate-800/80 border border-slate-700 p-3 rounded-xl flex-1">
          <span className="text-xs text-slate-300 font-semibold block mb-2">Recent Call Logs</span>
          {analytics.recent_calls.length === 0 ? (
            <p className="text-slate-500 text-xs italic">No call logs recorded yet.</p>
          ) : (
            <div className="space-y-2">
              {analytics.recent_calls.map((call, idx) => (
                <div key={idx} className="p-2 bg-slate-900/80 rounded-lg border border-slate-800 text-xs flex justify-between items-center">
                  <div>
                    <div className="font-mono text-[10px] text-slate-400">{call.call_id}</div>
                    <div className="text-slate-200 mt-0.5 truncate max-w-[160px]">{call.reason}</div>
                  </div>
                  <span className={`px-2 py-0.5 text-[9px] font-bold rounded ${
                    call.outcome === 'SUCCESS' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
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

  return (
    <main className="h-screen w-screen bg-slate-950">
      {!token ? (
        <div className="h-full flex flex-col items-center justify-center text-white">
          <div className="p-8 bg-slate-900 border border-slate-800 rounded-2xl text-center max-w-md">
            <h1 className="text-2xl font-bold mb-2 text-cyan-400">Roshni Financial AI</h1>
            <p className="text-sm text-slate-400 mb-6">Day 8: Real-Time Call Analytics Dashboard</p>
            <button
              onClick={connectToRoom}
              className="px-6 py-3 bg-gradient-to-r from-cyan-500 to-blue-600 rounded-xl font-semibold hover:opacity-90 transition"
            >
              Start Session / Connect
            </button>
          </div>
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
    </main>
  );
}