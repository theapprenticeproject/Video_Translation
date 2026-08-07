import { api } from './client';

export interface SignedUrlResponse {
  upload_url: string;
  object_name: string;
}

/** Step 0.1 — get a signed GCS PUT URL for the given file. */
export async function getSignedUploadUrl(
  filename: string,
  contentType: string,
  token?: string,
): Promise<SignedUrlResponse> {
  return api<SignedUrlResponse>('/api/upload/signed-url', {
    method: 'POST',
    body: JSON.stringify({ filename, content_type: contentType }),
  }, token);
}

/** Step 0.2 — PUT the file directly to GCS (browser → GCS, bypasses backend). */
export function uploadFileToGCS(
  uploadUrl: string,
  file: File,
  onProgress?: (fraction: number) => void,
): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('PUT', uploadUrl);
    xhr.setRequestHeader('Content-Type', file.type);

    if (onProgress) {
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) onProgress(e.loaded / e.total);
      };
    }

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve();
      } else {
        reject(new Error(`GCS upload failed: ${xhr.status}`));
      }
    };

    xhr.onerror = () => reject(new Error('Network error during file upload'));
    xhr.onabort = () => reject(new Error('File upload was aborted'));
    xhr.send(file);
  });
}

const BASE = (import.meta.env.VITE_API_SERVER_URL as string) || '';

/** Step 0.2 (Fallback) — Upload file directly to backend endpoint using FormData. */
export function uploadFileDirectToBackend(
  file: File,
  token?: string,
  onProgress?: (fraction: number) => void,
): Promise<SignedUrlResponse> {
  return new Promise((resolve, reject) => {
    const formData = new FormData();
    formData.append('file', file);

    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${BASE}/api/upload/direct`);
    if (token) {
      xhr.setRequestHeader('Authorization', `Bearer ${token}`);
    }

    if (onProgress) {
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) onProgress(e.loaded / e.total);
      };
    }

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const res = JSON.parse(xhr.responseText) as SignedUrlResponse;
          resolve(res);
        } catch (e) {
          reject(e);
        }
      } else {
        reject(new Error(`Direct backend upload failed: ${xhr.status}`));
      }
    };

    xhr.onerror = () => reject(new Error('Network error during direct upload'));
    xhr.onabort = () => reject(new Error('Direct upload was aborted'));
    xhr.send(formData);
  });
}

