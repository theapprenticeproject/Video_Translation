import { useState, useContext, useCallback, useEffect, useRef, useMemo } from 'react';
import { useAuth } from '@clerk/react';
import { WizardContext } from '../App';
import { updateSegments, approveJob, translateSingle } from '../api/jobs';
import { getVoices, type Voice } from '../api/voices';
import { previewTTS } from '../api/tts';
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

  // Live preview state
  const [previewingSegment, setPreviewingSegment] = useState<number | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Universal voice & emotion state
  const [globalVoiceId, setGlobalVoiceId] = useState<string>(defaultVoiceId || '');
  const [globalSpeed, setGlobalSpeed] = useState<number>(1.0);
  const [globalStability, setGlobalStability] = useState<number>(0.5);
  const [globalStyle, setGlobalStyle] = useState<number>(0.0);
  const [showEmotionGuide, setShowEmotionGuide] = useState<boolean>(false);

  // Credit / token tracker
  const [previewedChars, setPreviewedChars] = useState<number>(0);
  const [previewCount, setPreviewCount] = useState<number>(0);

  const totalCharacters = useMemo(() => {
    return segments.reduce((sum, seg) => sum + (seg.translated ? seg.translated.length : 0), 0);
  }, [segments]);

  // Translation state
  const [translatingSegment, setTranslatingSegment] = useState<number | null>(null);

  const handleRetranslate = useCallback(async (segIndex: number, originalText: string) => {
    try {
      setTranslatingSegment(segIndex);
      const token = await getToken() ?? undefined;
      const newTranslation = await translateSingle(originalText, language, token);
      
      setSegments(prev =>
        prev.map(seg => seg.index === segIndex ? { ...seg, translated: newTranslation } : seg)
      );
    } catch (err) {
      console.error('Failed to retranslate:', err);
      alert(err instanceof Error ? err.message : 'Retranslate failed');
    } finally {
      setTranslatingSegment(null);
    }
  }, [language, getToken]);

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

  const handlePreview = useCallback(async (seg: Segment) => {
    try {
      if (audioRef.current) {
        audioRef.current.pause();
      }
      
      setPreviewingSegment(seg.index);
      // Track preview credit burn
      setPreviewedChars(prev => prev + (seg.translated ? seg.translated.length : 0));
      setPreviewCount(prev => prev + 1);

      const token = await getToken() ?? undefined;
      const url = await previewTTS(
        seg.translated,
        seg.voice_id || defaultVoiceId,
        seg.speed ?? 1.0,
        seg.stability ?? 0.5,
        seg.style ?? 0.0,
        token
      );
      
      const audio = new Audio(url);
      audioRef.current = audio;
      
      audio.onended = () => {
        setPreviewingSegment(null);
      };
      
      await audio.play();
    } catch (err) {
      console.error('Preview failed:', err);
      alert(err instanceof Error ? err.message : 'Preview failed');
      setPreviewingSegment(null);
    }
  }, [defaultVoiceId, getToken]);

  const applyGlobalSettings = useCallback(() => {
    if (!confirm(`Apply delivery settings (Speed: ${globalSpeed.toFixed(2)}x, Stability: ${Math.round(globalStability * 100)}%, Style: ${Math.round(globalStyle * 100)}%) to all ${segments.length} chunks?\n\n(Note: Assigned speaker voices will NOT be changed.)`)) {
      return;
    }

    setSegments(prev =>
      prev.map(seg => ({
        ...seg,
        speed: globalSpeed,
        stability: globalStability,
        style: globalStyle,
      }))
    );
  }, [globalSpeed, globalStability, globalStyle, segments.length]);

  const applyGlobalSettingsToSameVoice = useCallback(() => {
    const targetVoiceId = globalVoiceId || defaultVoiceId;
    const targetVoiceName = voices.find(v => v.voice_id === targetVoiceId)?.name || 'Selected Voice';
    const matchCount = segments.filter(s => (s.voice_id || defaultVoiceId) === targetVoiceId).length;

    if (matchCount === 0) {
      alert(`No chunks currently use "${targetVoiceName}".`);
      return;
    }

    if (!confirm(`Apply delivery settings (Speed: ${globalSpeed.toFixed(2)}x, Stability: ${Math.round(globalStability * 100)}%, Style: ${Math.round(globalStyle * 100)}%) to all ${matchCount} chunks assigned to "${targetVoiceName}"?`)) {
      return;
    }

    setSegments(prev =>
      prev.map(seg => {
        const segVoice = seg.voice_id || defaultVoiceId;
        if (segVoice === targetVoiceId) {
          return {
            ...seg,
            speed: globalSpeed,
            stability: globalStability,
            style: globalStyle,
          };
        }
        return seg;
      })
    );
  }, [globalVoiceId, defaultVoiceId, voices, segments, globalSpeed, globalStability, globalStyle]);

  const applySegmentSettingsToAll = useCallback((sourceSeg: Segment) => {
    const speed = sourceSeg.speed ?? 1.0;
    const stability = sourceSeg.stability ?? 0.5;
    const style = sourceSeg.style ?? 0.0;

    if (!confirm(`Apply this chunk's delivery settings (Speed: ${speed.toFixed(2)}x, Stability: ${Math.round(stability * 100)}%, Style: ${Math.round(style * 100)}%) to all ${segments.length} chunks?\n\n(Note: Assigned speaker voices will NOT be changed.)`)) {
      return;
    }

    setSegments(prev =>
      prev.map(s => ({
        ...s,
        speed,
        stability,
        style,
      }))
    );
  }, [segments.length]);

  const applySegmentSettingsToSameVoice = useCallback((sourceSeg: Segment) => {
    const speed = sourceSeg.speed ?? 1.0;
    const stability = sourceSeg.stability ?? 0.5;
    const style = sourceSeg.style ?? 0.0;
    const targetVoiceId = sourceSeg.voice_id || defaultVoiceId;
    const targetVoiceName = voices.find(v => v.voice_id === targetVoiceId)?.name || 'this voice';
    const matchCount = segments.filter(s => (s.voice_id || defaultVoiceId) === targetVoiceId).length;

    if (!confirm(`Apply delivery settings (Speed: ${speed.toFixed(2)}x, Stability: ${Math.round(stability * 100)}%, Style: ${Math.round(style * 100)}%) to all ${matchCount} chunks assigned to "${targetVoiceName}"?`)) {
      return;
    }

    setSegments(prev =>
      prev.map(s => {
        const segVoice = s.voice_id || defaultVoiceId;
        if (segVoice === targetVoiceId) {
          return {
            ...s,
            speed,
            stability,
            style,
          };
        }
        return s;
      })
    );
  }, [defaultVoiceId, voices, segments]);

  const handleMoveWordToPrev = useCallback((segIndex: number, wordIndex: number) => {
    setSegments(prev => {
      const targetSegIndex = prev.findIndex(s => s.index === segIndex);
      if (targetSegIndex <= 0) return prev;
      
      const currentSeg = prev[targetSegIndex];
      const prevSeg = prev[targetSegIndex - 1];
      
      if (!currentSeg.words || currentSeg.words.length <= 1) return prev;
      
      const wordToMove = currentSeg.words[wordIndex];
      const newCurrentWords = [...currentSeg.words];
      newCurrentWords.splice(wordIndex, 1);
      
      const newPrevWords = [...(prevSeg.words || []), wordToMove];
      
      const newSegments = [...prev];
      newSegments[targetSegIndex - 1] = {
        ...prevSeg,
        words: newPrevWords,
        original: newPrevWords.map(w => w.text).join(' '),
        end: wordToMove.end
      };
      newSegments[targetSegIndex] = {
        ...currentSeg,
        words: newCurrentWords,
        original: newCurrentWords.map(w => w.text).join(' '),
        start: newCurrentWords[0].start
      };
      
      return newSegments;
    });
  }, []);

  const handleMoveWordToNext = useCallback((segIndex: number, wordIndex: number) => {
    setSegments(prev => {
      const targetSegIndex = prev.findIndex(s => s.index === segIndex);
      if (targetSegIndex === -1 || targetSegIndex >= prev.length - 1) return prev;
      
      const currentSeg = prev[targetSegIndex];
      const nextSeg = prev[targetSegIndex + 1];
      
      if (!currentSeg.words || currentSeg.words.length <= 1) return prev;
      
      const wordToMove = currentSeg.words[wordIndex];
      const newCurrentWords = [...currentSeg.words];
      newCurrentWords.splice(wordIndex, 1);
      
      const newNextWords = [wordToMove, ...(nextSeg.words || [])];
      
      const newSegments = [...prev];
      newSegments[targetSegIndex] = {
        ...currentSeg,
        words: newCurrentWords,
        original: newCurrentWords.map(w => w.text).join(' '),
        end: newCurrentWords[newCurrentWords.length - 1].end
      };
      newSegments[targetSegIndex + 1] = {
        ...nextSeg,
        words: newNextWords,
        original: newNextWords.map(w => w.text).join(' '),
        start: wordToMove.start
      };
      
      return newSegments;
    });
  }, []);

  const handleSplitChunk = useCallback((segIndex: number, wordIndex: number) => {
    setSegments(prev => {
      const targetSegIndex = prev.findIndex(s => s.index === segIndex);
      if (targetSegIndex === -1) return prev;
      
      const currentSeg = prev[targetSegIndex];
      if (!currentSeg.words || currentSeg.words.length <= 1) return prev;
      if (wordIndex <= 0 || wordIndex >= currentSeg.words.length) return prev;
      
      const wordsLeft = currentSeg.words.slice(0, wordIndex);
      const wordsRight = currentSeg.words.slice(wordIndex);
      
      const leftSeg = {
        ...currentSeg,
        words: wordsLeft,
        original: wordsLeft.map((w: { text: string }) => w.text).join(' '),
        end: wordsLeft[wordsLeft.length - 1].end,
        translated: "" // Clear translation since segment meaning changed
      };
      
      const rightSeg = {
        ...currentSeg,
        words: wordsRight,
        original: wordsRight.map((w: { text: string }) => w.text).join(' '),
        start: wordsRight[0].start,
        translated: ""
      };
      
      const newSegments = [...prev];
      newSegments.splice(targetSegIndex, 1, leftSeg, rightSeg);
      
      // Update indices
      return newSegments.map((s, idx) => ({ ...s, index: idx }));
    });
  }, []);

  const handleWordClick = useCallback((segIndex: number, wordIndex: number, totalWords: number, isLastSeg: boolean) => {
    if (wordIndex === 0 && segIndex > 0) {
      if (confirm('Move this word to the previous segment?')) {
        handleMoveWordToPrev(segIndex, wordIndex);
      }
    } else if (wordIndex === totalWords - 1 && !isLastSeg) {
      if (confirm('Move this word to the next segment?')) {
        handleMoveWordToNext(segIndex, wordIndex);
      }
    } else {
       // Splitting
       if (totalWords > 1 && wordIndex > 0 && wordIndex < totalWords) {
           if (confirm('Split the segment starting at this word?')) {
               handleSplitChunk(segIndex, wordIndex);
           }
       }
    }
  }, [handleMoveWordToPrev, handleMoveWordToNext, handleSplitChunk]);

  const handleMergeWithNext = useCallback((indexToMerge: number) => {
    setSegments(prev => {
      const segIndex = prev.findIndex(s => s.index === indexToMerge);
      if (segIndex === -1 || segIndex === prev.length - 1) return prev;
      
      const current = prev[segIndex];
      const next = prev[segIndex + 1];
      
      const merged = {
        ...current,
        original: `${current.original} ${next.original}`,
        translated: `${current.translated} ${next.translated}`,
        end: next.end,
        words: [...(current.words || []), ...(next.words || [])]
      };
      
      const newSegments = [...prev];
      newSegments[segIndex] = merged;
      newSegments.splice(segIndex + 1, 1);
      
      // Update indices
      return newSegments.map((s, idx) => ({ ...s, index: idx }));
    });
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

      {/* Credit & Token Usage Dashboard */}
      <div className="credit-tracker-card">
        <div className="credit-tracker-stat">
          <span>Total Script:</span>
          <strong>{totalCharacters} characters</strong>
          <span style={{ opacity: 0.6 }}>· ~{totalCharacters} ElevenLabs credits</span>
        </div>
        <div className="credit-tracker-stat">
          <span className="credit-preview-badge">
            ⚡ Previews Burn: {previewedChars} chars ({previewCount} plays)
          </span>
        </div>
      </div>

      {/* Universal Delivery & Emotion Bar */}
      <div className="universal-voice-bar">
        <div className="universal-voice-bar__header">
          <div className="universal-voice-bar__title">
            <span>🎚️ Universal Voice & Emotion Settings</span>
            <button
              type="button"
              className="btn-info-guide"
              onClick={() => setShowEmotionGuide(true)}
              title="Click for Voice & Emotion Guide: How to tune Stability & Style"
              aria-label="Open Voice and Emotion Guide"
            >
              i
            </button>
          </div>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
            <button
              type="button"
              className="btn btn--small btn--primary"
              onClick={applyGlobalSettings}
              title="Apply speed, stability, and style to all chunks without changing their assigned voices"
            >
              🌐 Apply Settings to All Chunks
            </button>
            <button
              type="button"
              className="btn btn--small btn--ghost"
              onClick={applyGlobalSettingsToSameVoice}
              title={`Apply speed, stability, and style only to chunks that use "${voices.find(v => v.voice_id === (globalVoiceId || defaultVoiceId))?.name || 'this voice'}"`}
            >
              👥 Apply to Chunks with Same Voice
            </button>
          </div>
        </div>

        <div className="universal-controls-grid">
          <div>
            <label style={{ display: 'block', fontSize: 'var(--t-xs)', color: 'var(--c-paper-dim)', marginBottom: '4px' }}>
              Voice
            </label>
            <select
              className="universal-voice-select"
              value={globalVoiceId || defaultVoiceId}
              onChange={(e) => setGlobalVoiceId(e.target.value)}
              aria-label="Universal Voice"
            >
              {voices.map((v) => (
                <option key={v.voice_id} value={v.voice_id}>
                  {v.name}
                </option>
              ))}
            </select>
          </div>

          <div className="universal-slider-wrap">
            <label>
              <span>Speed</span>
              <span>{globalSpeed.toFixed(2)}x</span>
            </label>
            <input
              type="range"
              min="0.7"
              max="1.2"
              step="0.05"
              value={globalSpeed}
              onChange={(e) => setGlobalSpeed(parseFloat(e.target.value))}
            />
          </div>

          <div className="universal-slider-wrap">
            <label>
              <span>Stability (Emotion)</span>
              <span>{Math.round(globalStability * 100)}%</span>
            </label>
            <input
              type="range"
              min="0.0"
              max="1.0"
              step="0.05"
              value={globalStability}
              onChange={(e) => setGlobalStability(parseFloat(e.target.value))}
            />
          </div>

          <div className="universal-slider-wrap">
            <label>
              <span>Style Boost</span>
              <span>{Math.round(globalStyle * 100)}%</span>
            </label>
            <input
              type="range"
              min="0.0"
              max="1.0"
              step="0.05"
              value={globalStyle}
              onChange={(e) => setGlobalStyle(parseFloat(e.target.value))}
            />
          </div>
        </div>
      </div>

      {/* Column headers */}
      <div className="review-tracks-header" aria-hidden="true">
        <span className="track-header-label track-header-label--time">Time</span>
        <span className="track-header-label track-header-label--original">Original</span>
        <span className="track-header-label track-header-label--words">Interactive Words</span>
        <span className="track-header-label track-header-label--translation">Translation & Voice Settings</span>
      </div>

      {/* Segments — dual tape track layout */}
      <div className="review-segments" role="table" aria-label="Translation segments">
        <div role="rowgroup">
          {segments.map((seg, i) => (
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

              {/* Words track (interactive) */}
              <div className="segment-track segment-track--words" role="cell">
                <div className="word-editor-container">
                  {seg.words && seg.words.length > 0 ? (
                    seg.words.map((word: { text: string; start: number; end: number }, wIdx: number) => {
                      const isFirst = wIdx === 0;
                      const isLast = wIdx === seg.words!.length - 1;
                      const isEdge = isFirst || isLast;
                      return (
                        <span 
                          key={wIdx} 
                          className={`word-pill ${isEdge ? 'word-pill--edge' : ''}`}
                          onClick={() => handleWordClick(seg.index, wIdx, seg.words!.length, i === segments.length - 1)}
                          title={isFirst ? "Click to move word UP to previous chunk" : isLast ? "Click to move word DOWN to next chunk" : "Click to split the chunk starting at this word"}
                        >
                          {word.text}
                        </span>
                      );
                    })
                  ) : (
                    <span className="timecode" style={{ opacity: 0.5 }}>No word data available</span>
                  )}
                </div>
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
                
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '4px' }}>
                  <span className="segment-char-count">{seg.translated?.length || 0} chars</span>
                  <button
                    type="button"
                    className="btn btn--small btn--ghost"
                    onClick={() => handleRetranslate(seg.index, seg.original)}
                    disabled={translatingSegment === seg.index}
                    title="Ask AI to retranslate this sentence from scratch (useful after splitting/merging)"
                    style={{ fontSize: 'var(--t-xs)', padding: '2px 8px' }}
                  >
                    {translatingSegment === seg.index ? '⏳ Translating...' : '✨ AI Retranslate'}
                  </button>
                </div>

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
                    
                    <div className="control-slider" style={{ marginTop: 'var(--sp-2)', display: 'flex', gap: 'var(--sp-2)', flexWrap: 'wrap', alignItems: 'center' }}>
                      <button 
                        type="button" 
                        className="btn btn--small btn--ghost" 
                        onClick={() => handlePreview(seg)}
                        disabled={previewingSegment !== null && previewingSegment !== seg.index}
                      >
                        {previewingSegment === seg.index ? '🔊 Playing...' : '▶ Preview Voice'}
                      </button>
                      <button
                        type="button"
                        className="btn-apply-same-voice"
                        onClick={() => applySegmentSettingsToSameVoice(seg)}
                        title="Copy this chunk's speed, stability, and style only to chunks with the same voice"
                      >
                        👥 Apply to same voice ({segments.filter(s => (s.voice_id || defaultVoiceId) === (seg.voice_id || defaultVoiceId)).length})
                      </button>
                      <button
                        type="button"
                        className="btn-apply-all-segment"
                        onClick={() => applySegmentSettingsToAll(seg)}
                        title="Copy this chunk's speed, stability, and style to all other chunks (keeps voices)"
                      >
                        🌐 Apply to all chunks (keeps voices)
                      </button>
                    </div>
                  </div>
                )}
                {i < segments.length - 1 && (
                  <button
                    type="button"
                    className="btn btn--small btn--ghost"
                    style={{ marginTop: 'var(--sp-2)', borderTop: '1px dashed var(--c-graphite-dim)', paddingTop: 'var(--sp-2)', width: '100%' }}
                    onClick={() => handleMergeWithNext(seg.index)}
                    title="Merge this segment with the next one for better emotional context"
                  >
                    🔗 Merge Down
                  </button>
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

      {/* Emotion & Voice Guide Modal */}
      {showEmotionGuide && (
        <div className="emotion-guide-backdrop" onClick={() => setShowEmotionGuide(false)}>
          <div className="emotion-guide-modal" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h2>🎙️ How to Dial In Voice & Human Emotion</h2>
              <button 
                type="button" 
                className="btn btn--small btn--ghost" 
                onClick={() => setShowEmotionGuide(false)}
                style={{ fontSize: '1.2rem', padding: '0 6px', lineHeight: 1 }}
              >
                ✕
              </button>
            </div>

            <div className="emotion-guide-section">
              <h3>1. Stability (Expression Control)</h3>
              <p>
                <strong>30% – 45% (High Emotion):</strong> Yields energetic, lively, and dynamic vocal delivery. Best for enthusiastic dialogue, student/teacher interactions, exclamation points, and curious questions (e.g. <em>"Haan ma'am!"</em> or <em>"Kyun hota hai?"</em>).
              </p>
              <p style={{ marginTop: '6px' }}>
                <strong>50% – 65% (Natural):</strong> Balanced everyday conversational tone with natural pitch inflection.
              </p>
              <p style={{ marginTop: '6px' }}>
                <strong>70% – 85% (Calm / Steady):</strong> Strict, consistent pacing. Best for formal narration or factual reading.
              </p>
            </div>

            <div className="emotion-guide-section">
              <h3>2. Style Boost (Persona & Drama)</h3>
              <p>
                <strong>15% – 30%:</strong> Exaggerates the speaker's emotional character. Recommended if the voice sounds too flat or monotonic. Keep under 40% to avoid audio artifacts.
              </p>
            </div>

            <div className="emotion-guide-section">
              <h3>3. Speed Adjustment</h3>
              <p>
                <strong>0.90x – 0.95x:</strong> Slows down delivery for complex educational explanations or to allow students time to digest.
              </p>
              <p style={{ marginTop: '6px' }}>
                <strong>1.05x – 1.15x:</strong> Speeds up lengthy translated sentences so they comfortably fit before visual slide transitions.
              </p>
            </div>

            <div className="emotion-guide-section">
              <h3>4. Emotional Chunking Tip</h3>
              <p>
                Short phrases like <em>"Haan ma'am"</em> or <em>"Bilkul sahi"</em> sound robotic when isolated in their own chunk because AI lacks context. Use <strong>[🔗 Merge Down]</strong> to combine them with the following sentence so the AI understands the emotional flow!
              </p>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 'var(--sp-2)' }}>
              <button 
                type="button" 
                className="btn btn--primary" 
                onClick={() => setShowEmotionGuide(false)}
              >
                Got It!
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
