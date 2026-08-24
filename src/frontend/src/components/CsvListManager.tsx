import { useCallback, useEffect, useRef, useState } from 'react';

import {
  deleteCsvList,
  listCsvLists,
  type CsvListInfo,
  uploadCsvList,
} from '../services/csvListsApi';

interface CsvListManagerProps {
  onChanged?: () => void;
}

const readableError = (error: unknown): string =>
  error instanceof Error ? error.message : 'Unexpected CSV list error';

export const CsvListManager = ({ onChanged }: CsvListManagerProps) => {
  const [lists, setLists] = useState<CsvListInfo[]>([]);
  const [name, setName] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async () => {
    try {
      setError('');
      setLists(await listCsvLists());
    } catch (err) {
      setError(readableError(err));
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const handleUpload = async () => {
    const file = fileRef.current?.files?.[0];
    if (!file) {
      setError('Choose a CSV file first.');
      return;
    }

    try {
      setBusy(true);
      setError('');
      setMessage('');
      const imported = await uploadCsvList(file, name);
      setMessage(`Imported ${imported.name} (${imported.book_count.toLocaleString()} books).`);
      setName('');
      if (fileRef.current) fileRef.current.value = '';
      await refresh();
      onChanged?.();
    } catch (err) {
      setError(readableError(err));
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async (list: CsvListInfo) => {
    if (!window.confirm(`Delete CSV list “${list.name}”?`)) return;

    try {
      setBusy(true);
      setError('');
      setMessage('');
      await deleteCsvList(list.id);
      setMessage(`Deleted ${list.name}.`);
      await refresh();
      onChanged?.();
    } catch (err) {
      setError(readableError(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="csv-list-manager" aria-labelledby="csv-list-manager-title">
      <div className="csv-list-manager__header">
        <div>
          <h3 id="csv-list-manager-title">Imported CSV Lists</h3>
          <p>
            Upload one CSV per list. <strong>Title</strong> is required; Author, ISBN, ISBN13,
            and Rank are optional. Uploading the same list name replaces that list.
          </p>
        </div>
      </div>

      <div className="csv-list-manager__upload">
        <label>
          <span>List name (optional)</span>
          <input
            type="text"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Defaults to the CSV filename"
            disabled={busy}
          />
        </label>
        <label>
          <span>CSV file</span>
          <input ref={fileRef} type="file" accept=".csv,text/csv" disabled={busy} />
        </label>
        <button type="button" onClick={() => void handleUpload()} disabled={busy}>
          {busy ? 'Working…' : 'Import CSV'}
        </button>
      </div>

      {error && <p className="csv-list-manager__error" role="alert">{error}</p>}
      {message && <p className="csv-list-manager__message" role="status">{message}</p>}

      {lists.length === 0 ? (
        <p className="csv-list-manager__empty">No CSV lists have been imported yet.</p>
      ) : (
        <div className="csv-list-manager__lists">
          {lists.map((list) => (
            <div className="csv-list-manager__row" key={list.id}>
              <div>
                <strong>{list.name}</strong>
                <div>{list.book_count.toLocaleString()} books · {list.filename}</div>
              </div>
              <button
                type="button"
                onClick={() => void handleDelete(list)}
                disabled={busy}
                aria-label={`Delete ${list.name}`}
              >
                Delete
              </button>
            </div>
          ))}
        </div>
      )}
    </section>
  );
};

export default CsvListManager;
