import { Button } from '@/components/ui/button';

function WelcomeImage() {
  return (
    <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-blue-100 text-blue-600 dark:bg-blue-950 dark:text-blue-400 shadow-sm">
      <svg
        width="32"
        height="32"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <rect x="3" y="4" width="18" height="16" rx="2" />
        <line x1="3" y1="10" x2="21" y2="10" />
        <line x1="7" y1="15" x2="7.01" y2="15" />
        <line x1="11" y1="15" x2="13" y2="15" />
      </svg>
    </div>
  );
}

interface WelcomeViewProps {
  startButtonText: string;
  onStartCall: () => void;
}

export const WelcomeView = ({
  startButtonText,
  onStartCall,
  ref,
}: React.ComponentProps<'div'> & WelcomeViewProps) => {
  return (
    <div ref={ref}>
      <section className="bg-background flex flex-col items-center justify-center text-center px-4 max-w-lg mx-auto">
        <WelcomeImage />

        <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
          Roshni — AI Financial Assistant
        </h1>

        <p className="text-muted-foreground max-w-md pt-2 text-sm leading-6 font-normal">
          Get instant guidance on Indian banking services, FD interest rates, loan applications, and UPI payments in English or Hinglish.
        </p>

        {/* Quick Sample Topics */}
        <div className="mt-4 flex flex-wrap justify-center gap-2 text-xs text-slate-500">
          <span className="rounded-md bg-slate-100 px-2.5 py-1 dark:bg-slate-800">💡 FD Interest Rates</span>
          <span className="rounded-md bg-slate-100 px-2.5 py-1 dark:bg-slate-800">💳 Digital UPI Payments</span>
          <span className="rounded-md bg-slate-100 px-2.5 py-1 dark:bg-slate-800">📄 Personal Loan Steps</span>
        </div>

        <Button
          size="lg"
          onClick={onStartCall}
          className="mt-6 w-64 rounded-full font-mono text-xs font-bold tracking-wider uppercase bg-blue-600 hover:bg-blue-700 text-white shadow-md transition-all active:scale-95"
        >
          {startButtonText || "Start Financial Consultation"}
        </Button>

        <div className="mt-4 inline-flex items-center gap-1.5 rounded-full bg-amber-50 px-3 py-1 text-xs text-amber-700 dark:bg-amber-950/40 dark:text-amber-400 border border-amber-200 dark:border-amber-900">
          🔒 Never share your OTP, PIN, or confidential passwords.
        </div>
      </section>

      <div className="fixed bottom-5 left-0 flex w-full items-center justify-center">
        <p className="text-muted-foreground max-w-prose pt-1 text-xs leading-5 font-normal text-pretty md:text-sm">
          Powered by{' '}
          <span className="font-semibold text-foreground">Murf Falcon</span> & LiveKit
        </p>
      </div>
    </div>
  );
};