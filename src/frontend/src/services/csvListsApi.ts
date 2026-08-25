import { getApiBase } from '../utils/basePath';

export interface CsvListInfo {
  id: string;
  name: string;
  filename: string;
  book_count: number;
  counts: Record<string, number>;
  processing: boolean;
}

const CSV_LISTS_URL = `${getApiBase()}/csv-lists`;

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null;

const isCsvListInfo = (value: unknown): value is CsvListInfo =>
  isRecord(value) &&
  typeof value.id === 'string' &&
  typeof value.name === 'string' &&
  typeof value.filename === 'string' &&
  typeof value.book_count === 'number' &&
  isRecord(value.counts) &&
  typeof value.processing === 'boolean';

const responseError = async (response: Response): Promise<Error> => {
  let message = `Request failed (${response.status})`;
  try {
    const payload = (await response.json()) as unknown;
    if (isRecord(payload) && typeof payload.error === 'string') message = payload.error;
  } catch {
    // Keep the HTTP fallback message when the response is not JSON.
  }
  return new Error(message);
};

export const listCsvLists = async (): Promise<CsvListInfo[]> => {
  const response = await fetch(CSV_LISTS_URL, { credentials: 'same-origin' });
  if (!response.ok) throw await responseError(response);

  const payload = (await response.json()) as unknown;
  if (!Array.isArray(payload) || !payload.every(isCsvListInfo)) {
    throw new Error('Invalid CSV list response');
  }
  return payload;
};

export const uploadCsvList = async (file: File, name?: string): Promise<CsvListInfo> => {
  const body = new FormData();
  body.append('file', file);
  if (name?.trim()) body.append('name', name.trim());

  const response = await fetch(CSV_LISTS_URL, {
    method: 'POST',
    credentials: 'same-origin',
    body,
  });
  if (!response.ok) throw await responseError(response);

  const payload = (await response.json()) as unknown;
  if (!isCsvListInfo(payload)) throw new Error('Invalid CSV upload response');
  return payload;
};

export const deleteCsvList = async (listId: string): Promise<void> => {
  const response = await fetch(`${CSV_LISTS_URL}/${encodeURIComponent(listId)}`, {
    method: 'DELETE',
    credentials: 'same-origin',
  });
  if (!response.ok) throw await responseError(response);
};

export const queueAllCsvList = async (listId: string): Promise<boolean> => {
  const response = await fetch(`${CSV_LISTS_URL}/${encodeURIComponent(listId)}/queue-all`, {
    method: 'POST',
    credentials: 'same-origin',
  });
  if (!response.ok) throw await responseError(response);
  const payload = (await response.json()) as unknown;
  return isRecord(payload) && payload.started === true;
};
