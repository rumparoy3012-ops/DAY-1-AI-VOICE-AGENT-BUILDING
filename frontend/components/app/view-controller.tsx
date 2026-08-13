'use client';

import { useTheme } from 'next-themes';
import { AnimatePresence, motion } from 'motion/react';
import { useSessionContext, useAgent } from '@livekit/components-react';
import type { AppConfig } from '@/app-config';
import { AgentSessionView_01 } from '@/components/agents-ui/blocks/agent-session-view-01';
import { WelcomeView } from '@/components/app/welcome-view';

const VIEW_MOTION_PROPS = {
  variants: {
    visible: { opacity: 1 },
    hidden: { opacity: 0 },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
  transition: { duration: 0.5, ease: 'linear' as const },
};

interface ViewControllerProps {
  appConfig: AppConfig;
}

export function ViewController({ appConfig }: ViewControllerProps) {
  const { isConnected, start } = useSessionContext();
  const agent = useAgent();
  const { resolvedTheme } = useTheme();

  // Active speaking indicator state
  const isAgentSpeaking = agent?.state === 'speaking';

  return (
    <AnimatePresence mode="wait">
      {/* 1. STATE: READY (Welcome view) */}
      {!isConnected && (
        <motion.div
          key="welcome"
          {...VIEW_MOTION_PROPS}
        >
          <WelcomeView
            startButtonText={appConfig.startButtonText || "Start Financial Consultation"}
            onStartCall={start}
          />
        </motion.div>
      )}

      {/* 2, 3 & 4. STATES: CONNECTING, LISTENING & SPEAKING */}
      {isConnected && (
        <motion.div
          key="session-wrapper"
          className="relative h-full w-full"
          {...VIEW_MOTION_PROPS}
        >
          {/* Top Status Banner (Fulfills Step 2 & Step 3) */}
          <div className="absolute top-6 left-1/2 -translate-x-1/2 z-50 flex items-center gap-2 rounded-full px-4 py-1.5 shadow-lg backdrop-blur-md bg-background/80 border border-border">
            <span
              className={`h-3 w-3 rounded-full animate-pulse ${
                isAgentSpeaking ? 'bg-green-500' : 'bg-blue-500'
              }`}
            />
            <span className="text-xs font-semibold tracking-wide uppercase text-foreground">
              {isAgentSpeaking ? 'Roshni is Speaking' : 'Listening to you...'}
            </span>
          </div>

          <AgentSessionView_01
            supportsChatInput={appConfig.supportsChatInput}
            supportsVideoInput={appConfig.supportsVideoInput}
            supportsScreenShare={appConfig.supportsScreenShare}
            isPreConnectBufferEnabled={appConfig.isPreConnectBufferEnabled}
            audioVisualizerType={appConfig.audioVisualizerType}
            audioVisualizerColor={
              resolvedTheme === 'dark'
                ? appConfig.audioVisualizerColorDark
                : appConfig.audioVisualizerColor
            }
            audioVisualizerColorShift={appConfig.audioVisualizerColorShift}
            audioVisualizerBarCount={appConfig.audioVisualizerBarCount}
            audioVisualizerGridRowCount={appConfig.audioVisualizerGridRowCount}
            audioVisualizerGridColumnCount={appConfig.audioVisualizerGridColumnCount}
            audioVisualizerRadialBarCount={appConfig.audioVisualizerRadialBarCount}
            audioVisualizerRadialRadius={appConfig.audioVisualizerRadialRadius}
            audioVisualizerWaveLineWidth={appConfig.audioVisualizerWaveLineWidth}
            className="fixed inset-0"
          />
        </motion.div>
      )}
    </AnimatePresence>
  );
}