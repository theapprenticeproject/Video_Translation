import { useRef, useState, useContext, useCallback } from 'react';
import { useAuth } from '@clerk/react';
import { WizardContext } from '../App';
import { getSignedUploadUrl, uploadFileToGCS } from '../api/upload';

const ACCEPTED = ['.mp3', '.mp4', '.wav', '.m4a', '.webm'];
const ACCEPTED_MIME = ['audio/mpeg', 'audio/mp4', 'video/mp4', 'audio/wav', 'audio/x-wav', 'audio/webm', 'video/webm'];

function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function UploadStep() {
  const { setObjectName, goTo } = useContext(WizardContext);
  const { getToken } = useAuth();
  const inputRef = useRef<HTMLInputElement>(null);

  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const handleFile = useCallback((f: File) => {
    if (!ACCEPTED_MIME.includes(f.type) && !ACCEPTED.some(ext => f.name.endsWith(ext))) {
      setError(`Unsupported format. Accepted: ${ACCEPTED.join(', ')}`);
      return;
    }
    setFile(f);
    setError(null);
  }, []);

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(true);
  }, []);

  const onDragLeave = useCallback(() => setDragging(false), []);

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
      const { upload_url, object_name } = await getSignedUploadUrl(file.name, file.type || 'application/octet-stream', token);
      await uploadFileToGCS(upload_url, file, setProgress);
      setObjectName(object_name);
      goTo(2);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  }, [file, setObjectName, goTo, getToken]);

  return (
    <div className="upload-step">
      <h1 className="step__heading">Drop your media.</h1>
      <p className="step__sub">
        Audio or video — the original track is extracted before anything else touches it.
      </p>

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
            stroke="currentColor" strokeWidth="1.5" aria-hidden="true"
            style={{ color: 'var(--c-amber)', flex: 'none' }}
          >
            <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22" />
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
    </div>
  );
}
