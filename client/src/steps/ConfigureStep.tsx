import { useState, useContext, useCallback } from 'react';
import { useAuth } from '@clerk/react';
import { WizardContext } from '../App';
import { createJob } from '../api/jobs';

const LANGUAGES = [
  { code: 'mr', label: 'Marathi' },
  { code: 'hi', label: 'Hindi' },
  { code: 'pa', label: 'Punjabi' },
  { code: 'kn', label: 'Kannada' },
];

export default function ConfigureStep() {
  const { objectName, language, voiceId, setLanguage, setVoiceId, setJobId, goTo } =
    useContext(WizardContext);
  const { getToken } = useAuth();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleStart = useCallback(async () => {
    if (!objectName || !voiceId.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const token = await getToken() ?? undefined;
      const { job_id } = await createJob(objectName, language, voiceId.trim(), token);
      setJobId(job_id);
      goTo(3);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not start job');
    } finally {
      setLoading(false);
    }
  }, [objectName, language, voiceId, setJobId, goTo, getToken]);

  return (
    <div className="configure-step">
      <h1 className="step__heading">Configure output.</h1>
      <p className="step__sub">
        Choose the target language and the voice that will deliver the translation.
      </p>

      <div className="configure-fields">
        {/* Language toggle */}
        <div className="field">
          <label className="field__label" id="lang-label">Target language</label>
          <div
            className="lang-toggle"
            role="group"
            aria-labelledby="lang-label"
          >
            {LANGUAGES.map((l) => (
              <button
                key={l.code}
                type="button"
                className={`lang-toggle__option${language === l.code ? ' lang-toggle__option--active' : ''}`}
                onClick={() => setLanguage(l.code)}
                aria-pressed={language === l.code}
              >
                {l.label}
              </button>
            ))}
          </div>
        </div>

        {/* Voice ID — "patch cable" label */}
        <div className="field">
          <label className="field__label" htmlFor="voice-id">Voice ID</label>
          <div className="voice-input-wrap">
            <span className="voice-label-tag" aria-hidden="true">ID ·</span>
            <input
              id="voice-id"
              type="text"
              className="voice-input"
              value={voiceId}
              onChange={(e) => setVoiceId(e.target.value)}
              placeholder="ElevenLabs voice ID…"
              spellCheck={false}
              autoComplete="off"
              autoCapitalize="off"
            />
          </div>
          <p className="field__hint">
            Find voice IDs in your ElevenLabs library under Voice → ID.
          </p>
        </div>

        {/* File reference */}
        {objectName && (
          <div className="field">
            <span className="field__label">Source file</span>
            <span
              style={{
                fontFamily: 'var(--f-mono)',
                fontSize: 'var(--t-xs)',
                color: 'var(--c-paper-dim)',
                wordBreak: 'break-all',
              }}
            >
              {objectName.split('/').pop()}
            </span>
          </div>
        )}
      </div>

      {error && <p className="error-msg" role="alert" style={{ marginTop: 'var(--sp-6)' }}>{error}</p>}

      <div className="btn-row">
        <button
          className="btn btn--primary"
          disabled={!voiceId.trim() || loading}
          onClick={handleStart}
        >
          {loading ? 'Starting…' : 'Start Translation'}
        </button>
        <button className="btn btn--ghost" onClick={() => goTo(1)}>
          ← Back
        </button>
      </div>
    </div>
  );
}
