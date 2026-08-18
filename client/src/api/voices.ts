import { api } from './client';

export interface Voice {
  voice_id: string;
  name: string;
  speed?: number;
  stability?: number;
  style?: number;
}

export async function getVoices(token?: string): Promise<Voice[]> {
  return api<Voice[]>('/api/voices', undefined, token);
}

export async function saveVoice(voice: Voice, token?: string): Promise<void> {
  await api<null>('/api/voices', {
    method: 'POST',
    body: JSON.stringify(voice),
  }, token);
}

export async function deleteVoice(voiceId: string, token?: string): Promise<void> {
  await api<null>(`/api/voices/${voiceId}`, {
    method: 'DELETE',
  }, token);
}
