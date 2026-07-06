import type { AskResponse, UploadResponse } from "@/types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "";

async function parseJsonResponse<T>(response: Response): Promise<T> {
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const message =
      typeof payload?.detail === "string"
        ? payload.detail
        : `Request failed with status ${response.status}`;
    throw new Error(message);
  }
  return payload as T;
}

export async function askQuestion(question: string, topK = 5): Promise<AskResponse> {
  const response = await fetch(`${API_BASE_URL}/api/ask`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ question, top_k: topK }),
  });

  return parseJsonResponse<AskResponse>(response);
}

export function uploadDocument(
  file: File,
  onProgress: (progress: number) => void,
): Promise<UploadResponse> {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    const formData = new FormData();
    formData.append("file", file);

    request.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    };

    request.onload = () => {
      try {
        const payload = JSON.parse(request.responseText || "{}");
        if (request.status >= 200 && request.status < 300) {
          onProgress(100);
          resolve(payload as UploadResponse);
          return;
        }
        reject(new Error(payload?.detail ?? `Upload failed with status ${request.status}`));
      } catch (error) {
        reject(error);
      }
    };

    request.onerror = () => reject(new Error("Upload failed. Check the API server and network."));
    request.open("POST", `${API_BASE_URL}/upload`);
    request.send(formData);
  });
}
