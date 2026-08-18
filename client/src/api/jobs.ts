import { api } from './client';

export interface Segment {
  index: number;
  original: string;
  translated: string;
  start: number;
  end: number;
  voice_id?: string;
  speed?: number;
  stability?: number;
  style?: number;
}

export type JobStatus =
  | 'processing'
  | 'awaiting_review'
  | 'complete'
  | 'failed'
  | 'unknown';

export interface Job {
  job_id: string;
  status: JobStatus;
  stage: string;
  error: string | null;
  gcs_original: string | null;
  gcs_processed: string | null;
  source_language: string | null;
  language: string | null;
  voice_id: string | null;
  segments: Segment[];
}

export interface JobHistoryItem {
  job_id: string;
  status: JobStatus;
  stage: string;
  error: string | null;
  filename: string;
  created_at: number;
  source_language: string;
  language: string;
  voice_id: string;
}

export interface CreateJobResponse {
  job_id: string;
}

export interface DownloadResponse {
  download_url: string;
}

export async function createJob(
  objectName: string,
  sourceLanguage: string,
  language: string,
  voiceId: string,
  token?: string,
): Promise<CreateJobResponse> {
  return api<CreateJobResponse>('/api/jobs', {
    method: 'POST',
    body: JSON.stringify({
      object_name: objectName,
      source_language: sourceLanguage,
      language,
      voice_id: voiceId,
    }),
  }, token);
}

export async function pollJob(jobId: string, token?: string): Promise<Job> {
  return api<Job>(`/api/jobs/${jobId}`, undefined, token);
}

export async function updateSegments(jobId: string, segments: Segment[], token?: string): Promise<void> {
  await api<null>(`/api/jobs/${jobId}/segments`, {
    method: 'PATCH',
    body: JSON.stringify({ segments }),
  }, token);
}

export async function approveJob(jobId: string, token?: string): Promise<void> {
  await api<null>(`/api/jobs/${jobId}/approve`, { method: 'POST' }, token);
}

export async function getDownloadUrl(jobId: string, token?: string): Promise<DownloadResponse> {
  return api<DownloadResponse>(`/api/jobs/${jobId}/download`, undefined, token);
}

export async function listJobs(token?: string): Promise<JobHistoryItem[]> {
  return api<JobHistoryItem[]>('/api/jobs', undefined, token);
}
