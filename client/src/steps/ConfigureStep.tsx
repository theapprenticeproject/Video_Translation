import { useState, useContext, useCallback, useEffect } from 'react';
import { useAuth } from '@clerk/react';
import { WizardContext } from '../App';
import { createJob } from '../api/jobs';
import { getVoices, saveVoice, deleteVoice, type Voice } from '../api/voices';

const LANGUAGES = [
  { code: 'hi', label: 'Hindi' },
  { code: 'mr', label: 'Marathi' },
  { code: 'en', label: 'English' },
  { code: 'pa', label: 'Punjabi' },
  { code: 'kn', label: 'Kannada' },
];

export default function ConfigureStep() {
  const {
    objectName,
    sourceLanguage,
    language,
    voiceId,
    setSourceLanguage,
    setLanguage,
    setVoiceId,
    setJobId,
    goTo,
  } = useContext(WizardContext);
  
  const { getToken } = useAuth();

  const [voices, setVoices] = useState<Voice[]>([]);
  const [loading, setLoading] = useState(false);
  const [voicesLoading, setVoicesLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // New voice registration form state
  const [showAddForm, setShowAddForm] = useState(false);
  const [newVoiceName, setNewVoiceName] = useState('');
  const [newVoiceId, setNewVoiceId] = useState('');
  const [addError, setAddError] = useState<string | null>(null);
  const [addingVoice, setAddingVoice] = useState(false);

  // Fetch voices on load
  const loadVoices = useCallback(async () => {
    setVoicesLoading(true);
    try {
      const token = await getToken() ?? undefined;
      const list = await getVoices(token);
      setVoices(list);
      // Select first voice if none is active or active is not in the list
      if (list.length > 0 && (!voiceId || !list.some(v => v.voice_id === voiceId))) {
        setVoiceId(list[0].voice_id);
      }
    } catch (err) {
      console.error('Failed to load voices:', err);
    } finally {
      setVoicesLoading(false);
    }
  }, [getToken, voiceId, setVoiceId]);

  useEffect(() => {
    void loadVoices();
  }, []);

  const handleStart = useCallback(async () => {
    if (!objectName || !voiceId.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const token = await getToken() ?? undefined;
      const { job_id } = await createJob(objectName, sourceLanguage, language, voiceId.trim(), token);
      setJobId(job_id);
      goTo(3);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not start job');
    } finally {
      setLoading(false);
    }
  }, [objectName, sourceLanguage, language, voiceId, setJobId, goTo, getToken]);

  const handleAddVoice = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newVoiceName.trim() || !newVoiceId.trim()) return;
    
    setAddingVoice(true);
    setAddError(null);
    try {
      const token = await getToken() ?? undefined;
      await saveVoice({
        voice_id: newVoiceId.trim(),
        name: newVoiceName.trim(),
      }, token);
      
      // Reset form
      setNewVoiceName('');
      setNewVoiceId('');
      setShowAddForm(false);
      
      // Reload voices list and set selected voice ID
      const list = await getVoices(token);
      setVoices(list);
      setVoiceId(newVoiceId.trim());
    } catch (err) {
      setAddError(err instanceof Error ? err.message : 'Failed to save voice ID');
    } finally {
      setAddingVoice(false);
    }
  };

  const handleDeleteVoice = async (idToDelete: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this voice ID?')) return;
    
    try {
      const token = await getToken() ?? undefined;
      await deleteVoice(idToDelete, token);
      
      const list = voices.filter(v => v.voice_id !== idToDelete);
      setVoices(list);
      
      if (voiceId === idToDelete && list.length > 0) {
        setVoiceId(list[0].voice_id);
      }
    } catch (err) {
      console.error('Failed to delete voice:', err);
    }
  };

  const isDefaultVoice = (id: string) => {
    const defaults = ["21m00Tcm4TlvDq8ikWAM", "AZnzlk1XvdvUeBnXmlld", "EXAVITQu4vr4xnSDxMaL", "ErXwobaYiN019PkySvjV", "TX3293t7o4WbqthJuOC3"];
    return defaults.includes(id);
  };

  return (
    <div className="configure-step">
      <h1 className="step__heading">Configure output.</h1>
      <p className="step__sub">
        Choose languages and selecting the voice to render the dubbed translation.
      </p>

      <div className="configure-fields">
        {/* Source Language selection */}
        <div className="field">
          <label className="field__label" id="source-lang-label">Source language (Spoken in Video)</label>
          <div
            className="lang-toggle"
            role="group"
            aria-labelledby="source-lang-label"
          >
            {LANGUAGES.map((l) => (
              <button
                key={`src-${l.code}`}
                type="button"
                className={`lang-toggle__option${sourceLanguage === l.code ? ' lang-toggle__option--active' : ''}`}
                onClick={() => setSourceLanguage(l.code)}
                aria-pressed={sourceLanguage === l.code}
              >
                {l.label}
              </button>
            ))}
          </div>
        </div>

        {/* Target Language selection */}
        <div className="field">
          <label className="field__label" id="lang-label">Target language (Output Translation)</label>
          <div
            className="lang-toggle"
            role="group"
            aria-labelledby="lang-label"
          >
            {LANGUAGES.map((l) => (
              <button
                key={`tgt-${l.code}`}
                type="button"
                className={`lang-toggle__option${language === l.code ? ' lang-toggle__option--active' : ''}`}
                onClick={() => setLanguage(l.code)}
                aria-pressed={language === l.code}
                disabled={l.code === sourceLanguage} // Avoid translating to the same language
              >
                {l.label}
              </button>
            ))}
          </div>
        </div>

        {/* Voice Selection */}
        <div className="field">
          <div className="field-header-row">
            <label className="field__label" htmlFor="voice-select">ElevenLabs Voice</label>
            <button 
              type="button" 
              className="btn-text-action"
              onClick={() => setShowAddForm(!showAddForm)}
            >
              {showAddForm ? '✕ Close Form' : '+ Add Voice ID'}
            </button>
          </div>

          {/* Add custom voice ID form */}
          {showAddForm && (
            <form className="add-voice-form" onSubmit={handleAddVoice}>
              <h3>Register Custom Voice</h3>
              <div className="add-voice-grid">
                <input
                  type="text"
                  placeholder="Voice Name (e.g. Rachel)"
                  value={newVoiceName}
                  onChange={(e) => setNewVoiceName(e.target.value)}
                  className="voice-input"
                  required
                />
                <input
                  type="text"
                  placeholder="ElevenLabs Voice ID"
                  value={newVoiceId}
                  onChange={(e) => setNewVoiceId(e.target.value)}
                  className="voice-input"
                  required
                />
              </div>
              {addError && <p className="error-msg-mini">{addError}</p>}
              <button type="submit" className="btn btn--small btn--primary" disabled={addingVoice}>
                {addingVoice ? 'Adding…' : 'Save Voice'}
              </button>
            </form>
          )}

          {voicesLoading ? (
            <div className="voices-loading-text">Loading voices…</div>
          ) : (
            <div className="voice-input-wrap">
              <span className="voice-label-tag" aria-hidden="true">VOICE ·</span>
              <select
                id="voice-select"
                className="voice-select"
                value={voiceId}
                onChange={(e) => setVoiceId(e.target.value)}
              >
                {voices.map((v) => (
                  <option key={v.voice_id} value={v.voice_id}>
                    {v.name} {isDefaultVoice(v.voice_id) ? '(Preset)' : '(Custom)'}
                  </option>
                ))}
              </select>
              
              {/* Delete custom voice button */}
              {voiceId && !isDefaultVoice(voiceId) && (
                <button
                  type="button"
                  className="btn-voice-delete"
                  onClick={(e) => handleDeleteVoice(voiceId, e)}
                  title="Delete this custom voice"
                >
                  ✕ Remove
                </button>
              )}
            </div>
          )}

          <p className="field__hint">
            Preset voices are provided, or you can register your custom ElevenLabs Voice IDs.
          </p>
        </div>

        {/* Source file reference */}
        {objectName && (
          <div className="field">
            <span className="field__label">Source file</span>
            <span
              className="source-file-badge"
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
