import { ReactNode, useEffect } from 'react';
import { toast as sonnerToast } from 'sonner';
import { useAgent, useSessionContext } from '@livekit/components-react';
import { WarningIcon } from '@phosphor-icons/react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

interface ToastProps {
  title: ReactNode;
  description: ReactNode;
}

function toastAlert(toast: ToastProps) {
  const { title, description } = toast;

  return sonnerToast.custom(
    (id) => (
      <Alert onClick={() => sonnerToast.dismiss(id)} className="bg-accent w-full md:w-[364px] border-destructive/50">
        <WarningIcon weight="bold" className="text-destructive" />
        <AlertTitle>{title}</AlertTitle>
        {description && <AlertDescription>{description}</AlertDescription>}
      </Alert>
    ),
    { duration: 10_000 }
  );
}

export function useAgentErrors() {
  const agent = useAgent();
  const { isConnected, end } = useSessionContext();

  // 1. Listen for LiveKit Agent Failures
  useEffect(() => {
    if (isConnected && agent.state === 'failed') {
      const reasons = agent.failureReasons;

      toastAlert({
        title: 'Session ended',
        description: (
          <>
            {reasons.length > 1 && (
              <ul className="list-inside list-disc">
                {reasons.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            )}
            {reasons.length === 1 && <p className="w-full">{reasons[0]}</p>}
            <p className="w-full pt-1">
              <a
                target="_blank"
                rel="noopener noreferrer"
                href="https://docs.livekit.io/agents/start/voice-ai/"
                className="whitespace-nowrap underline"
              >
                See quickstart guide
              </a>
            </p>
          </>
        ),
      });

      end();
    }
  }, [agent, isConnected, end]);

  // 2. Explicitly handle Microphone Permission Denials (Fulfills Step 4)
  useEffect(() => {
    if (typeof window === 'undefined' || !navigator.permissions) return;

    navigator.permissions.query({ name: 'microphone' as PermissionName }).then((permissionStatus) => {
      const checkPermission = () => {
        if (permissionStatus.state === 'denied') {
          toastAlert({
            title: 'Microphone Permission Blocked',
            description: (
              <p className="text-xs text-muted-foreground">
                Microphone access is blocked in your browser. Please click the lock/settings icon in the URL bar, set Microphone to <strong>Allow</strong>, and refresh the page to speak with Roshni.
              </p>
            ),
          });
        }
      };

      checkPermission();
      permissionStatus.onchange = checkPermission;
    }).catch(() => {
      // Graceful fallback for browsers that do not support permission queries
    });
  }, []);
}