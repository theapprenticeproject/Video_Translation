import { useState, useContext, useCallback, useEffect } from 'react';
import { useAuth } from '@clerk/react';
import { WizardContext } from '../App';
import { updateSegments, approveJob } from '../api/jobs';
import { getVoices, type Voice } from '../api/voices';
import type { Segment } from '../api/jobs';

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export default function ReviewStep() {
  const { jobId, language, voiceId: defaultVoiceId, goTo, segments: initialSegments } = useContext(WizardContext);
  const { getToken } = useAuth();

  const [segments, setSegments] = useState<Segment[]>(initialSegments);
  const [voices, setVoices] = useState<Voice[]>([]);
  const [expandedSegments, setExpandedSegments] = useState<Record<number, boolean>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load voices on mount
  useEffect(() => {
    void (async () => {
      try {
        const token = await getToken() ?? undefined;
        const list = await getVoices(token);
        setVoices(list);
      } catch (err) {
        console.error('Failed to fetch voices in ReviewStep:', err);
      }
    })();
  }, [getToken]);

  const handleTranslationChange = useCallback((index: number, value: string) => {
    setSegments(prev =>
      prev.map(seg => seg.index === index ? { ...seg, translated: value } : seg)
    );
  }, []);

  const handleSegmentSettingChange = useCallback((index: number, key: keyof Segment, value: any) => {
    setSegments(prev =>
      prev.map(seg => seg.index === index ? { ...seg, [key]: value } : seg)
    );
  }, []);

  const toggleSettings = useCallback((index: number) => {
    setExpandedSegments(prev => ({ ...prev, [index]: !prev[index] }));
  }, []);

  const handleApprove = useCallback(async () => {
    if (!jobId) return;
    setLoading(true);
    setError(null);
    try {
      const token = await getToken() ?? undefined;
      // Filter out segments with undefined/default values or pass defaults explicitly
      const sanitizedSegments = segments.map(seg => ({
        ...seg,
        voice_id: seg.voice_id || defaultVoiceId || undefined,
        speed: seg.speed ?? 1.0,
        stability: seg.stability ?? 0.5,
        style: seg.style ?? 0.0,
      }));

      await updateSegments(jobId, sanitizedSegments, token);
      await approveJob(jobId, token);
      goTo(3); // briefly back to progress for TTS generation
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to approve');
    } finally {
      setLoading(false);
    }
  }, [jobId, segments, defaultVoiceId, goTo, getToken]);

  const LANG_NAMES: Record<string, string> = { 
    mr: 'Marathi', 
    hi: 'Hindi', 
    pa: 'Punjabi', 
    kn: 'Kannada',
    en: 'English' 
  };
  const langName = LANG_NAMES[language] ?? language;

  return (
    <div className="review-step">
      <h1 className="step__heading">Review translations.</h1>
      <p className="step__sub">
        Customize speaker voice, adjust speed and stability for each segment, then approve to generate the audio.
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
        <span className="track-header-label track-header-label--translation">Translation & Voice Settings</span>
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

              {/* Translation track (editable + custom controls) */}
              <div className="segment-track segment-track--translation" role="cell">
                <div className="segment-track-header">
                  <div className="segment-speaker-select-wrap">
                    <span className="speaker-tag" aria-hidden="true">VOICE ·</span>
                    <select
                      className="segment-voice-select"
                      value={seg.voice_id || defaultVoiceId}
                      onChange={(e) => handleSegmentSettingChange(seg.index, 'voice_id', e.target.value)}
                      aria-label={`Speaker for segment ${seg.index + 1}`}
                    >
                      {voices.map((v) => (
                        <option key={v.voice_id} value={v.voice_id}>
                          {v.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <button
                    type="button"
                    className={`btn-segment-settings${expandedSegments[seg.index] ? ' btn-segment-settings--active' : ''}`}
                    onClick={() => toggleSettings(seg.index)}
                    aria-label={`Toggle voice settings for segment ${seg.index + 1}`}
                  >
                    ⚙️ Settings
                  </button>
                </div>

                <textarea
                  className="segment-translation-input"
                  value={seg.translated}
                  onChange={(e) => handleTranslationChange(seg.index, e.target.value)}
                  aria-label={`Translation for segment ${seg.index + 1}`}
                  lang={language}
                  rows={2}
                />

                {expandedSegments[seg.index] && (
                  <div className="segment-voice-controls">
                    <div className="control-slider">
                      <div className="slider-label-row">
                        <span>Speed</span>
                        <span>{(seg.speed ?? 1.0).toFixed(2)}x</span>
                      </div>
                      <input
                        type="range"
                        min="0.7"
                        max="1.2"
                        step="0.05"
                        value={seg.speed ?? 1.0}
                        onChange={(e) => handleSegmentSettingChange(seg.index, 'speed', parseFloat(e.target.value))}
                        className="slider-input"
                      />
                    </div>

                    <div className="control-slider">
                      <div className="slider-label-row">
                        <span>Stability (Expression)</span>
                        <span>{Math.round((seg.stability ?? 0.5) * 100)}%</span>
                      </div>
                      <input
                        type="range"
                        min="0.0"
                        max="1.0"
                        step="0.05"
                        value={seg.stability ?? 0.5}
                        onChange={(e) => handleSegmentSettingChange(seg.index, 'stability', parseFloat(e.target.value))}
                        className="slider-input"
                      />
                      <span className="slider-hint">
                        Lower stability yields more animated, emotional delivery.
                      </span>
                    </div>

                    <div className="control-slider">
                      <div className="slider-label-row">
                        <span>Style Boost</span>
                        <span>{Math.round((seg.style ?? 0.0) * 100)}%</span>
                      </div>
                      <input
                        type="range"
                        min="0.0"
                        max="1.0"
                        step="0.05"
                        value={seg.style ?? 0.0}
                        onChange={(e) => handleSegmentSettingChange(seg.index, 'style', parseFloat(e.target.value))}
                        className="slider-input"
                      />
                    </div>
                  </div>
                )}
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
