import { useState, useContext, useCallback } from 'react';
import { WizardContext } from '../App';
import { updateSegments, approveJob } from '../api/jobs';
import type { Segment } from '../api/jobs';

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export default function ReviewStep() {
  const { jobId, language, goTo, segments: initialSegments } = useContext(WizardContext);

  const [segments, setSegments] = useState<Segment[]>(initialSegments);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleTranslationChange = useCallback((index: number, value: string) => {
    setSegments(prev =>
      prev.map(seg => seg.index === index ? { ...seg, translated: value } : seg)
    );
  }, []);

  const handleApprove = useCallback(async () => {
    if (!jobId) return;
    setLoading(true);
    setError(null);
    try {
      await updateSegments(jobId, segments);
      await approveJob(jobId);
      goTo(3); // briefly back to progress for TTS generation
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to approve');
    } finally {
      setLoading(false);
    }
  }, [jobId, segments, goTo]);

  const langName = language === 'mr' ? 'Marathi' : language === 'pa' ? 'Punjabi' : 'Hindi';

  return (
    <div className="review-step">
      <h1 className="step__heading">Review translations.</h1>
      <p className="step__sub">
        Edit the {langName} translations directly — then approve to generate the dubbed audio.
      </p>

      <div className="review-meta">
        <span className="review-meta__item">
          <strong>{segments.length}</strong> segments
        </span>
        <span className="review-meta__item">
          Target: <strong translate="no">{langName}</strong>
        </span>
      </div>

      {/* Column headers */}
      <div className="review-tracks-header" aria-hidden="true">
        <span />
        <span className="track-header-label track-header-label--original">Original</span>
        <span className="track-header-label track-header-label--translation">Translation — edit freely</span>
      </div>

      {/* Segments — dual tape track layout */}
      <div className="review-segments" role="table" aria-label="Translation segments">
        <div role="rowgroup">
          {segments.map((seg) => (
            <div key={seg.index} className="segment-row" role="row">
              {/* Timecode column */}
              <div className="segment-time" role="cell" aria-label={`Segment ${seg.index + 1} at ${formatTime(seg.start)}`}>
                <span className="timecode">{formatTime(seg.start)}</span>
                <div className="segment-connector" aria-hidden="true" />
              </div>

              {/* Original track (read-only) */}
              <div className="segment-track segment-track--original" role="cell">
                <p className="segment-original-text" lang="hi">{seg.original}</p>
              </div>

              {/* Translation track (editable) */}
              <div className="segment-track" role="cell">
                <textarea
                  className="segment-translation-input"
                  value={seg.translated}
                  onChange={(e) => handleTranslationChange(seg.index, e.target.value)}
                  aria-label={`Translation for segment ${seg.index + 1}`}
                  lang={language}
                  rows={1}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {error && <p className="error-msg" role="alert">{error}</p>}

      {/* Sticky approve bar */}
      <div className="review-actions">
        <button
          className="btn btn--teal"
          disabled={loading}
          onClick={handleApprove}
        >
          {loading ? 'Submitting…' : 'Approve & Generate Audio'}
        </button>
        <span className="review-count">
          {segments.length} segments · {langName}
        </span>
      </div>
    </div>
  );
}
