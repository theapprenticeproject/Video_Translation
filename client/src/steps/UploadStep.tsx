import { useRef, useState, useContext, useCallback, useEffect } from 'react';
import { useAuth } from '@clerk/react';
import { WizardContext } from '../App';
import { getSignedUploadUrl, uploadFileToGCS, uploadFileDirectToBackend, uploadFromUrl } from '../api/upload';
import { listJobs, pollJob, type JobHistoryItem } from '../api/jobs';

const ACCEPTED = ['.mp3', '.mp4', '.wav', '.m4a', '.aac', '.webm'];
const ACCEPTED_MIME = ['audio/mpeg', 'audio/mp4', 'video/mp4', 'audio/wav', 'audio/x-wav', 'audio/x-m4a', 'audio/aac', 'audio/webm', 'video/webm'];

function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(timestamp: number): string {
  if (!timestamp) return '';
  const date = new Date(timestamp * 1000);
  return date.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function UploadStep() {
  const { setObjectName, setJobId, setLanguage, setSourceLanguage, setVoiceId, setSegments, goTo } = useContext(WizardContext);
  const { getToken } = useAuth();
  const inputRef = useRef<HTMLInputElement>(null);

  const [uploadMode, setUploadMode] = useState<'file' | 'youtube' | 'drive'>('file');
  const [inputUrl, setInputUrl] = useState<string>('');
  const [urlLoading, setUrlLoading] = useState<boolean>(false);

  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  // History state
  const [history, setHistory] = useState<JobHistoryItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);

  // Load history on mount
  const loadHistory = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const token = await getToken() ?? undefined;
      const list = await listJobs(token);
      setHistory(list);
    } catch (err) {
      console.error('Failed to load project history:', err);
    } finally {
      setHistoryLoading(false);
    }
  }, [getToken]);

  useEffect(() => {
    void loadHistory();
  }, [loadHistory]);

  const handleFile = useCallback((f: File) => {
    setError(null);
    const ext = '.' + f.name.split('.').pop()?.toLowerCase();
    if (!ACCEPTED.includes(ext) && !ACCEPTED_MIME.includes(f.type)) {
      setError(`Format not supported. Please use: ${ACCEPTED.join(', ')}`);
      return;
    }
    setFile(f);
  }, []);

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(true);
  }, []);

  const onDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
  }, []);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  }, [handleFile]);

  const onInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) handleFile(f);
    // Reset so the same file can be picked again
    e.target.value = '';
  }, [handleFile]);

  const onKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      inputRef.current?.click();
    }
  }, []);

  const handleUpload = useCallback(async () => {
    if (!file) return;
    setUploading(true);
    setError(null);
    setProgress(0);
    try {
      const token = await getToken() ?? undefined;
      let finalObjectName = '';
      try {
        const { upload_url, object_name } = await getSignedUploadUrl(file.name, file.type || 'application/octet-stream', token);
        await uploadFileToGCS(upload_url, file, setProgress);
        finalObjectName = object_name;
      } catch (gcsErr) {
        console.warn('Direct GCS upload failed, falling back to direct server upload:', gcsErr);
        const res = await uploadFileDirectToBackend(file, token, setProgress);
        finalObjectName = res.object_name;
      }
      setObjectName(finalObjectName);
      goTo(2);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  }, [file, setObjectName, goTo, getToken]);

  const handleUrlImport = useCallback(async () => {
    if (!inputUrl.trim()) {
      setError('Please enter a valid link');
      return;
    }
    setError(null);
    setUrlLoading(true);
    try {
      const token = await getToken() ?? undefined;
      const res = await uploadFromUrl(inputUrl.trim(), token);
      setObjectName(res.object_name);
      goTo(2);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to import media from link');
    } finally {
      setUrlLoading(false);
    }
  }, [inputUrl, getToken, setObjectName, goTo]);

  const handleResumeProject = async (proj: JobHistoryItem) => {
    setError(null);
    setJobId(proj.job_id);
    setLanguage(proj.language);
    setSourceLanguage(proj.source_language);
    setVoiceId(proj.voice_id);
    
    if (proj.status === 'awaiting_review') {
      setUploading(true); // show generic loader spinner while fetching
      try {
        const token = await getToken() ?? undefined;
        const fullJob = await pollJob(proj.job_id, token);
        setSegments(fullJob.segments || []);
        goTo(4);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Could not fetch project segments');
      } finally {
        setUploading(false);
      }
    } else if (proj.status === 'complete') {
      goTo(5);
    } else {
      // processing / failed
      goTo(3);
    }
  };

  const getStageLabel = (stage: string) => {
    const labels: Record<string, string> = {
      extracting: 'Extracting audio',
      transcribing: 'Transcribing speech',
      translating: 'Translating segments',
      awaiting_review: 'Ready for review',
      generating_tts: 'Generating dubbed audio',
      done: 'Complete',
    };
    return labels[stage] || stage;
  };

  const getStatusClass = (status: string) => {
    if (status === 'complete') return 'history-item__badge--complete';
    if (status === 'failed') return 'history-item__badge--failed';
    if (status === 'awaiting_review') return 'history-item__badge--review';
    return 'history-item__badge--processing';
  };

  const getLangBadge = (lang: string) => {
    return lang.toUpperCase();
  };

  return (
    <div className="upload-step">
      <h1 className="step__heading">Drop your media.</h1>
      <p className="step__sub">
        Upload a file or paste a link from YouTube or Google Drive — audio is extracted cleanly before translation.
      </p>

      {/* Upload Mode Tabs */}
      <div className="upload-tabs" role="tablist">
        <button
          type="button"
          className={`upload-tab ${uploadMode === 'file' ? 'upload-tab--active' : ''}`}
          onClick={() => { setUploadMode('file'); setError(null); }}
        >
          📁 Upload File
        </button>
        <button
          type="button"
          className={`upload-tab ${uploadMode === 'youtube' ? 'upload-tab--active' : ''}`}
          onClick={() => { setUploadMode('youtube'); setError(null); }}
        >
          🔴 YouTube Link
        </button>
        <button
          type="button"
          className={`upload-tab ${uploadMode === 'drive' ? 'upload-tab--active' : ''}`}
          onClick={() => { setUploadMode('drive'); setError(null); }}
        >
          💾 Google Drive Link
        </button>
      </div>

      {uploadMode === 'file' ? (
        <>
          {/* Hidden file input */}
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPTED.join(',')}
            style={{ display: 'none' }}
            onChange={onInputChange}
            aria-label="Choose a media file to translate"
            tabIndex={-1}
          />

          {/* Cassette drop zone */}
          <div
            role="button"
            tabIndex={0}
            aria-label="Drop zone — click or drag a file here"
            className={`reel-dropzone${dragging ? ' reel-dropzone--dragging' : ''}`}
            onDragOver={onDragOver}
            onDragLeave={onDragLeave}
            onDrop={onDrop}
            onClick={() => inputRef.current?.click()}
            onKeyDown={onKeyDown}
          >
            {/* SVG Cassette tape outline */}
            <svg
              viewBox="0 0 260 178"
              fill="none"
              className="reel-dropzone__cassette"
              aria-hidden="true"
            >
              {/* Outer shell */}
              <rect
                className="cassette-shell"
                x="4" y="4" width="252" height="170" rx="14"
                strokeWidth="2"
              />
              {/* Left reel */}
              <circle className="cassette-reel" cx="80" cy="80" r="34" strokeWidth="2" />
              <circle className="cassette-reel" cx="80" cy="80" r="14" strokeWidth="2" />
              <circle className="cassette-reel-hub" cx="80" cy="80" r="5" />
              {/* Right reel */}
              <circle className="cassette-reel" cx="180" cy="80" r="34" strokeWidth="2" />
              <circle className="cassette-reel" cx="180" cy="80" r="14" strokeWidth="2" />
              <circle className="cassette-reel-hub" cx="180" cy="80" r="5" />
              {/* Tape path — from reels down to window */}
              <path
                className="cassette-shell"
                d="M 46 80 Q 46 144 90 144 L 170 144 Q 214 144 214 80"
                strokeWidth="1.5"
              />
              {/* Tape window opening at bottom */}
              <rect
                className="cassette-shell"
                x="78" y="136" width="104" height="28" rx="4"
                strokeWidth="2"
              />
              {/* Bottom label area */}
              <line
                x1="30" y1="158" x2="230" y2="158"
                className="cassette-shell"
                strokeWidth="1"
                strokeDasharray="3 4"
              />
            </svg>

            <div>
              <p className="reel-dropzone__hint">
                <strong>Click to browse</strong> or drag a file here
              </p>
              <p className="reel-dropzone__formats">{ACCEPTED.join('  ·  ')}</p>
            </div>
          </div>

          {/* Selected file info */}
          {file && (
            <div className="upload-selected">
              <svg
                width="18" height="18" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeWidth="2"
                style={{ color: 'var(--c-amber)', flexShrink: 0 }}
                aria-hidden="true"
              >
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
              <span className="upload-selected__name">{file.name}</span>
              <span className="upload-selected__size">{formatBytes(file.size)}</span>
              <button
                className="btn btn--ghost"
                style={{ padding: '4px 10px', fontSize: 'var(--t-xs)' }}
                onClick={(e) => { e.stopPropagation(); setFile(null); }}
                aria-label="Remove selected file"
              >
                ✕
              </button>
            </div>
          )}

          {/* Upload progress bar */}
          {uploading && (
            <div className="upload-progress" role="progressbar" aria-valuenow={Math.round(progress * 100)} aria-valuemin={0} aria-valuemax={100}>
              <div className="upload-progress__label">
                <span>Uploading…</span>
                <span>{Math.round(progress * 100)}%</span>
              </div>
              <div className="upload-progress__track">
                <div className="upload-progress__fill" style={{ width: `${progress * 100}%` }} />
              </div>
            </div>
          )}

          {error && <p className="error-msg" role="alert">{error}</p>}

          <div className="btn-row">
            <button
              className="btn btn--primary"
              disabled={!file || uploading}
              onClick={handleUpload}
            >
              {uploading ? 'Uploading…' : 'Upload & Continue'}
            </button>
          </div>
        </>
      ) : (
        /* YouTube / Google Drive URL Import Card */
        <div className="url-import-card">
          <div className="url-import-input-wrap">
            <label htmlFor="media-url-input">
              {uploadMode === 'youtube' ? 'YouTube Video URL' : 'Google Drive File Share Link'}
            </label>
            <input
              id="media-url-input"
              type="url"
              className="url-import-input"
              placeholder={
                uploadMode === 'youtube'
                  ? 'https://www.youtube.com/watch?v=... or https://youtu.be/...'
                  : 'https://drive.google.com/file/d/.../view?usp=sharing'
              }
              value={inputUrl}
              onChange={(e) => setInputUrl(e.target.value)}
              disabled={urlLoading}
            />
          </div>

          <p className="url-import-hint">
            {uploadMode === 'youtube' ? (
              <span>⚡ Videos will be fetched in highest quality. Public and unlisted videos are supported.</span>
            ) : (
              <span>⚠️ Important: Make sure your Drive link permissions are set to <strong>"Anyone with the link can view"</strong>.</span>
            )}
          </p>

          {error && <p className="error-msg" role="alert">{error}</p>}

          <div className="btn-row">
            <button
              className="btn btn--primary"
              disabled={!inputUrl.trim() || urlLoading}
              onClick={handleUrlImport}
            >
              {urlLoading ? '⏳ Fetching & Downloading Media…' : 'Fetch & Continue'}
            </button>
          </div>
        </div>
      )}

      {/* Project History Dashboard */}
      <div className="project-history-section">
        <h2 className="history__heading">Past Projects</h2>
        {historyLoading ? (
          <div className="history-loading">Loading project history…</div>
        ) : history.length === 0 ? (
          <div className="history-empty">No past translations found. Start by dropping a tape above!</div>
        ) : (
          <div className="history-list" role="list">
            {history.map((proj) => (
              <div 
                key={proj.job_id} 
                className="history-item"
                role="button"
                onClick={() => handleResumeProject(proj)}
                title="Click to resume project"
              >
                <div className="history-item__main">
                  <div className="history-item__file-info">
                    <span className="history-item__filename">{proj.filename}</span>
                    <span className="history-item__date">{formatDate(proj.created_at)}</span>
                  </div>
                  <div className="history-item__meta">
                    <span className="history-item__lang-direction">
                      {getLangBadge(proj.source_language)} → {getLangBadge(proj.language)}
                    </span>
                    <span className={`history-item__badge ${getStatusClass(proj.status)}`}>
                      {proj.status === 'processing' ? getStageLabel(proj.stage) : getStageLabel(proj.status)}
                    </span>
                  </div>
                </div>
                <div className="history-item__chevron">→</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
