'use client';

import {
  LiveKitRoom,
  RoomAudioRenderer,
  VoiceAssistantControlBar,
  useChat,
  useRoomContext,
  BarVisualizer,
  useTranscriptions,
} from '@livekit/components-react';
import { useState } from 'react';

function DashboardContent() {
  const { chatMessages } = useChat();
  const room = useRoomContext();
  const transcriptSegments = useTranscriptions();

  const allMessages = [
    ...transcriptSegments.map((segment) => ({
      id: segment.id,
      sender: segment.participantIdentity || 'Participant',
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
              Speak into your microphone. Transcripts will stream here live...
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

      {/* CENTER COLUMN: Audio Visualizer & Call Controls */}
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

        <div className="mb-6 w-full flex justify-center">
          <VoiceAssistantControlBar controls={{ leave: true }} />
        </div>
      </div>

      {/* RIGHT COLUMN: Human Escalation & Summary */}
      <div className="w-1/3 border-l border-slate-800 p-4 flex flex-col bg-slate-900/50">
        <h2 className="text-lg font-bold text-amber-400 mb-3 flex items-center gap-2">
          <span>🛡️</span> Human Escalation Center
        </h2>
        
        <div className="space-y-4">
          <div className="bg-slate-800/80 border border-slate-700 p-4 rounded-xl">
            <span className="text-xs text-slate-400 uppercase font-semibold">Active Rules</span>
            <ul className="text-xs text-slate-300 mt-2 space-y-1 list-disc list-inside">
              <li>Suspected Fraud / Unauthorized Transactions</li>
              <li>Custom Loan/Rate Approval Exceptions</li>
            </ul>
          </div>

          <div className="bg-slate-800/80 border border-amber-500/30 p-4 rounded-xl bg-amber-950/10">
            <span className="text-xs text-amber-400 uppercase font-semibold">Consent Protocol</span>
            <p className="text-xs text-slate-300 mt-1">
              Roshni explicitly asks for caller consent before generating escalation tickets or transmitting caller summaries.
            </p>
            <div className="mt-3 flex items-center gap-2">
              <span className="px-2 py-1 bg-amber-500/20 text-amber-300 text-[10px] font-mono rounded-md border border-amber-500/30">
                REF ID DISPATCH
              </span>
              <span className="px-2 py-1 bg-blue-500/20 text-blue-400 text-[10px] font-mono rounded-md border border-blue-500/30">
                MURF FALCON TTS
              </span>
            </div>
          </div>
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
            <p className="text-sm text-slate-400 mb-6">Day 7: Human Escalation & Permission Hand-off</p>
            <button
              onClick={connectToRoom}
              className="px-6 py-3 bg-gradient-to-r from-cyan-500 to-blue-600 rounded-xl font-semibold hover:opacity-90 transition"
            >
              Start Session / Connect
            </button>
          </div>
        </div>
      ) : (
        <LiveKitRoom serverUrl={url} token={token} connect={true} audio={true} video={false}>
          <DashboardContent />
          <RoomAudioRenderer />
        </LiveKitRoom>
      )}
    </main>
  );
}