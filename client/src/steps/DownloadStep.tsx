import { useEffect, useState, useContext, useCallback } from 'react';
import { useAuth } from '@clerk/react';
import { WizardContext } from '../App';
import { getDownloadUrl } from '../api/jobs';

export default function DownloadStep() {
  const { jobId, reset } = useContext(WizardContext);
  const { getToken } = useAuth();

  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId) return;
    let active = true;
    setLoading(true);

    void (async () => {
      try {
        const token = await getToken() ?? undefined;
        const { download_url } = await getDownloadUrl(jobId, token);
        if (active) {
          setDownloadUrl(download_url);
          setLoading(false);
        }
      } catch (err: unknown) {
        if (active) {
          setError(err instanceof Error ? err.message : 'Could not get download URL.');
          setLoading(false);
        }
      }
    })();

    return () => { active = false; };
  }, [jobId, getToken]);

  const handleDownload = useCallback(() => {
    if (!downloadUrl) return;
    window.open(downloadUrl, '_blank', 'noreferrer');
  }, [downloadUrl]);

  return (
    <div className="download-step">
      <h1 className="step__heading">
        {loading ? 'Finishing up.' : error ? 'Something went wrong.' : 'Recorded.'}
      </h1>

      {loading && (
        <div className="progress-status" style={{ marginTop: 0 }}>
          <div className="progress-indicator" aria-hidden="true" />
          <span className="progress-stage-name">Preparing download…</span>
        </div>
      )}

      {error && (
        <div className="progress-error" role="alert">
          <span className="progress-error__label">Error</span>
          <span className="progress-error__message">{error}</span>
          <div className="btn-row" style={{ marginTop: 'var(--sp-4)' }}>
            <button className="btn btn--ghost" onClick={reset}>Start over</button>
          </div>
        </div>
      )}

      {downloadUrl && !error && (
        <>
          <p className="step__sub">
            Your dubbed audio is ready. The download link expires in 15 minutes.
          </p>

          <div className="download-complete-mark">
            <div className="download-complete-dot" aria-hidden="true" />
            <span className="download-complete-label">Tape recorded</span>
          </div>

          <div className="download-file-info">
            {/* Audio file icon */}
            <svg
              className="download-file-icon"
              viewBox="0 0 32 32"
              fill="none"
              aria-hidden="true"
            >
              <rect x="2" y="2" width="28" height="28" rx="4" stroke="currentColor" strokeWidth="1.5" />
              <circle cx="11" cy="22" r="3" stroke="currentColor" strokeWidth="1.5" />
              <circle cx="22" cy="20" r="3" stroke="currentColor" strokeWidth="1.5" />
              <path d="M14 22V10l11-2v10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
            <div className="download-file-details">
              <div className="download-file-name">translation_{jobId?.slice(0, 8)}.mp3</div>
              <div className="download-file-type">MP3 · Dubbed audio</div>
            </div>
          </div>

          <div className="btn-row">
            {/* Eject-style download button */}
            <button
              className="btn btn--eject"
              onClick={handleDownload}
              aria-label="Download translated audio file"
            >
              <span className="eject-icon" aria-hidden="true">
                <span className="eject-icon__tri" />
                <span className="eject-icon__bar" />
              </span>
              Download
            </button>

            <button className="btn btn--ghost" onClick={reset}>
              New translation
            </button>
          </div>
        </>
      )}
    </div>
  );
}
