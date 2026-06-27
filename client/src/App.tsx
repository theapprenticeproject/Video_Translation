import { createContext, useCallback, useContext, useState } from 'react';
import TapeStrip from './components/TapeStrip';
import UploadStep from './steps/UploadStep';
import ConfigureStep from './steps/ConfigureStep';
import ProgressStep from './steps/ProgressStep';
import ReviewStep from './steps/ReviewStep';
import DownloadStep from './steps/DownloadStep';
import type { Segment } from './api/jobs';

export type Step = 1 | 2 | 3 | 4 | 5;

// ─── Wizard Context ──────────────────────────────────────────────
export interface WizardContextValue {
  step: Step;
  objectName: string | null;
  jobId: string | null;
  language: string;
  voiceId: string;
  subStage: string | null;
  segments: Segment[];

  goTo: (next: Step) => void;
  reset: () => void;
  setObjectName: (v: string) => void;
  setJobId: (v: string) => void;
  setLanguage: (v: string) => void;
  setVoiceId: (v: string) => void;
  setSubStage: (v: string | null) => void;
  setSegments: (v: Segment[]) => void;
}

const noop = () => {};

export const WizardContext = createContext<WizardContextValue>({
  step: 1,
  objectName: null,
  jobId: null,
  language: 'mr',
  voiceId: '',
  subStage: null,
  segments: [],
  goTo: noop,
  reset: noop,
  setObjectName: noop,
  setJobId: noop,
  setLanguage: noop,
  setVoiceId: noop,
  setSubStage: noop,
  setSegments: noop,
});

// ─── Hook shorthand ──────────────────────────────────────────────
export function useWizard() {
  return useContext(WizardContext);
}

// ─── View Transition helper ───────────────────────────────────────
function withTransition(fn: () => void) {
  if ('startViewTransition' in document) {
    document.startViewTransition(fn);
  } else {
    fn();
  }
}

// ─── App ─────────────────────────────────────────────────────────
export default function App() {
  const [step,       setStep]       = useState<Step>(1);
  const [objectName, setObjectName] = useState<string | null>(null);
  const [jobId,      setJobId]      = useState<string | null>(null);
  const [language,   setLanguage]   = useState('mr');
  const [voiceId,    setVoiceId]    = useState('');
  const [subStage,   setSubStage]   = useState<string | null>(null);
  const [segments,   setSegments]   = useState<Segment[]>([]);

  const goTo = useCallback((next: Step) => {
    withTransition(() => setStep(next));
  }, []);

  const reset = useCallback(() => {
    withTransition(() => {
      setStep(1);
      setObjectName(null);
      setJobId(null);
      setSubStage(null);
      setSegments([]);
    });
  }, []);

  // When job enters awaiting_review, pull segments from the most recent poll.
  // ProgressStep calls setSubStage but doesn't hold segments — ReviewStep reads
  // from context, which is fed by ProgressStep via a special path:
  // ProgressStep → sets subStage → App detects awaiting_review in poll → goTo(4)
  // The segments are passed via context after being fetched in ProgressStep.
  // We expose setSegments so ProgressStep can push them before advancing.

  const ctxValue: WizardContextValue = {
    step, objectName, jobId, language, voiceId, subStage, segments,
    goTo, reset,
    setObjectName,
    setJobId,
    setLanguage,
    setVoiceId,
    setSubStage,
    setSegments,
  };

  return (
    <WizardContext.Provider value={ctxValue}>
      <div className="layout">
        {/* ── Header: logo + tape strip ── */}
        <header className="layout__header">
          <div className="header-top">
            <span className="logo">
              Localizer<span className="logo__accent"> ·</span>
            </span>
          </div>
          <TapeStrip step={step} subStage={subStage} />
        </header>

        {/* ── Step content ── */}
        <main className="layout__main" id="main-content">
          {/* key forces remount on step change — triggers view-transition */}
          <div className="step-content" key={step}>
            {step === 1 && <UploadStep />}
            {step === 2 && <ConfigureStep />}
            {step === 3 && <ProgressStep />}
            {step === 4 && <ReviewStep />}
            {step === 5 && <DownloadStep />}
          </div>
        </main>
      </div>
    </WizardContext.Provider>
  );
}
