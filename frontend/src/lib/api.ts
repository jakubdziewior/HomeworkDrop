export interface ApiTask {
  id: number;
  title: string;
  description: string;
  deadline: string;
  created_by: number;
  created_at: string;
  updated_at: string;
  is_expired: boolean;
}

export interface ApiSubmission {
  id: number;
  task_id: number;
  student_id: number;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  sha256: string;
  submitted_at: string;
  updated_at: string;
  status: "submitted" | "graded";
  grade: number | null;
  feedback: string | null;
  graded_by: number | null;
  graded_at: string | null;
}

export const ALLOWED_EXTENSIONS = [".pdf", ".zip", ".docx", ".png", ".jpg", ".jpeg", ".txt", ".md"];
export const MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024;

export function extractErrorMessage(payload: unknown, fallback: string): string {
  if (payload && typeof payload === "object" && "detail" in payload) {
    const detail = (payload as { detail: unknown }).detail;
    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0];
      if (first && typeof first === "object" && "msg" in first) {
        const msg = String((first as { msg: unknown }).msg);
        return msg.replace(/^Value error,\s*/i, "");
      }
    }
  }
  return fallback;
}

export async function apiRequest<T>(
  url: string,
  options: RequestInit = {},
  fallbackError = "Wystąpił błąd podczas komunikacji z serwerem."
): Promise<T> {
  const res = await fetch(url, {
    credentials: "same-origin",
    cache: "no-store",
    ...options,
  });

  if (!res.ok) {
    const errBody = await res.json().catch(() => null);
    throw new Error(extractErrorMessage(errBody, fallbackError));
  }

  if (res.status === 204) {
    return undefined as T;
  }

  return (await res.json()) as T;
}
