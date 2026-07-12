import { useEffect, useRef, useState, useContext } from 'react';
import { useAuth } from '@clerk/react';
import { WizardContext } from '../App';
import { pollJob } from '../api/jobs';

const POLL_MS = 3000;

const PIPELINE = [
  { stage: 'extracting',      label: 'Extracting audio track' },
  { stage: 'transcribing',    label: 'Transcribing speech' },
  { stage: 'translating',     label: 'Translating segments' },
  { stage: 'awaiting_review', label: 'Ready for review' },
  { stage: 'generating_tts',  label: 'Generating dubbed audio' },
  { stage: 'done',            label: 'Complete' },
];

const STAGE_ORDER = PIPELINE.map(s => s.stage);

function stageIndex(stage: string): number {
  const i = STAGE_ORDER.indexOf(stage);
  return i === -1 ? 0 : i;
}

function stageLabel(stage: string): string {
  return PIPELINE.find(s => s.stage === stage)?.label ?? stage;
}

export default function ProgressStep() {
  const { jobId, setSubStage, setSegments, goTo } = useContext(WizardContext);
  const { getToken } = useAuth();

  const [currentStage, setCurrentStage] = useState('extracting');
  const [failed, setFailed] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const advancedRef = useRef(false);

  useEffect(() => {
    if (!jobId) return;
    advancedRef.current = false;

    const poll = async () => {
      try {
        const token = await getToken() ?? undefined;
        const job = await pollJob(jobId, token);
        setCurrentStage(job.stage);
        setSubStage(job.stage);

        if (job.status === 'awaiting_review' && !advancedRef.current) {
          advancedRef.current = true;
          clearInterval(timerRef.current!);
          // Push segments into context before navigating to Review
          setSegments(job.segments ?? []);
          goTo(4);
          return;
        }

        if (job.status === 'complete' && !advancedRef.current) {
          advancedRef.current = true;
          clearInterval(timerRef.current!);
          goTo(5);
          return;
        }

        if (job.status === 'failed') {
          clearInterval(timerRef.current!);
          setFailed(true);
          setErrorMsg(job.error ?? 'An unknown error occurred.');
        }
      } catch (err) {
        clearInterval(timerRef.current!);
        setFailed(true);
        setErrorMsg(err instanceof Error ? err.message : 'Could not reach the server.');
      }
    };

    void poll();
    timerRef.current = setInterval(() => { void poll(); }, POLL_MS);
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [jobId, goTo, setSubStage, setSegments, getToken]);

  const currentIdx = stageIndex(currentStage);

  return (
    <div className="progress-step">
      {/* Screen-reader live region */}
      <div className="sr-live" aria-live="polite" aria-atomic="true">
        {failed
          ? `Pipeline failed — ${errorMsg ?? ''}`
          : `Processing — ${stageLabel(currentStage)}`}
      </div>

      <h1 className="step__heading">Processing.</h1>
      <p className="step__sub">
        The pipeline is running. Usually 1–3 minutes depending on file length.
      </p>

      {failed ? (
        <div className="progress-error" role="alert">
          <span className="progress-error__label">Pipeline failed</span>
          <span className="progress-error__message">{errorMsg}</span>
          <div className="btn-row" style={{ marginTop: 'var(--sp-4)' }}>
            <button className="btn btn--ghost" onClick={() => goTo(2)}>
              ← Reconfigure
            </button>
          </div>
        </div>
      ) : (
        <div className="progress-stage-display">
          <div className="progress-status">
            <div className="progress-indicator" aria-hidden="true" />
            <span className="progress-stage-name">{stageLabel(currentStage)}</span>
          </div>

          <div className="progress-pipeline" role="list">
            {PIPELINE.map((s, i) => {
              const isDone   = i < currentIdx;
              const isActive = i === currentIdx;
              return (
                <div
                  key={s.stage}
                  role="listitem"
                  className={
                    'pipeline-step' +
                    (isActive ? ' pipeline-step--active' : '') +
                    (isDone   ? ' pipeline-step--done'   : '')
                  }
                >
                  <div className="pipeline-step__dot" aria-hidden="true" />
                  <span className="pipeline-step__label">{s.label}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
