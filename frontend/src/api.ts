import {currentLanguage,localError} from './presentation';

export class ApiError extends Error {
  constructor(message: string, public status: number, public originalMessage=message) { super(message); }
}

export async function post<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  const response = await fetch(path, {
    method: 'POST', headers: {'Content-Type': 'application/json','X-Requested-With':'Udyam'}, body: JSON.stringify(body), signal,
  });
  const result = await response.json();
  if (!response.ok) {
    const fields = result.errors?.map((error: {location: string[]; message: string}) => `${error.location.slice(1).join('.')}: ${error.message}`).join(' · ');
    const message=fields || (typeof result.detail === 'string' ? result.detail : result.detail?.message) || 'The request could not be completed.';
    throw new ApiError(localError(message,currentLanguage(),response.status), response.status,message);
  }
  return result as T;
}
