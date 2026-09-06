const API_SERVER_URL = import.meta.env.VITE_API_SERVER_URL as string;

export async function previewTTS(
  text: string,
  voiceId: string,
  speed: number = 1.0,
  stability: number = 0.5,
  style: number = 0.0,
  token?: string
): Promise<string> {
  const response = await fetch(`${API_SERVER_URL}/api/tts/preview`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({
      text,
      voice_id: voiceId,
      speed,
      stability,
      style,
    }),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || 'Failed to generate live preview');
  }

  const blob = await response.blob();
  return URL.createObjectURL(blob);
}
