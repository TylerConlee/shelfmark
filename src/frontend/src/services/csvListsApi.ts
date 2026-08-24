import { getApiBase } from '../utils/basePath';

export interface CsvListInfo {
  id: string;
  name: string;
  filename: string;
  book_count: number;
}

const CSV_LISTS_URL = `${getApiBase()}/csv-lists`;

const responseError = async (response: Response): Promise<Error> => {
  let message = `Request failed (${response.status})`;
  try {
    const payload = (await response.json()) as { error?: string };
    if (payload.error) message = payload.error;
  } catch {
    // Keep the HTTP fallback message when the response is not JSON.
  }
  return new Error(message);
};

export const listCsvLists = async (): Promise<CsvListInfo[]> => {
  const response = await fetch(CSV_LISTS_URL, { credentials: 'same-origin' });
  if (!response.ok) throw await responseError(response);
  return (await response.json()) as CsvListInfo[];
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
  return (await response.json()) as CsvListInfo;
};

export const deleteCsvList = async (listId: string): Promise<void> => {
  const response = await fetch(`${CSV_LISTS_URL}/${encodeURIComponent(listId)}`, {
    method: 'DELETE',
    credentials: 'same-origin',
  });
  if (!response.ok) throw await responseError(response);
};
