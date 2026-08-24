import { useCallback, useRef, useState } from 'react';

import { useMountEffect } from '../hooks/useMountEffect';
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
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async () => {
    try {
      setError('');
      setLists(await listCsvLists());
    } catch (err) {
      setError(readableError(err));
    }
  }, []);

  useMountEffect(() => {
    void refresh();
  });

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
      setPendingDeleteId(null);
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
    if (pendingDeleteId !== list.id) {
      setPendingDeleteId(list.id);
      setMessage(`Click “Confirm delete” to remove ${list.name}.`);
      return;
    }

    try {
      setBusy(true);
      setError('');
      setMessage('');
      await deleteCsvList(list.id);
      setMessage(`Deleted ${list.name}.`);
      setPendingDeleteId(null);
      await refresh();
      onChanged?.();
    } catch (err) {
      setError(readableError(err));
    } finally {
      setBusy(false);
    }
  };

  const inputClass =
    'mt-1 w-full rounded-lg border border-black/15 bg-white px-3 py-2 text-sm text-slate-900 ' +
    'outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 ' +
    'disabled:cursor-not-allowed disabled:opacity-50 dark:border-white/15 dark:bg-slate-900 ' +
    'dark:text-slate-100';

  return (
    <section className="space-y-4" aria-labelledby="csv-list-manager-title">
      <div>
        <h3 id="csv-list-manager-title" className="text-base font-semibold">
          Imported CSV Lists
        </h3>
        <p className="mt-1 text-sm opacity-70">
          Upload one CSV per list. <strong>Title</strong> is required; Author, ISBN, ISBN13,
          and Rank are optional. Uploading the same list name replaces that list.
        </p>
      </div>

      <div className="grid gap-3 rounded-xl border border-black/10 p-4 dark:border-white/10 md:grid-cols-2">
        <label className="text-sm font-medium">
          <span>List name (optional)</span>
          <input
            className={inputClass}
            type="text"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Defaults to the CSV filename"
            disabled={busy}
          />
        </label>
        <label className="text-sm font-medium">
          <span>CSV file</span>
          <input
            className={inputClass}
            ref={fileRef}
            type="file"
            accept=".csv,text/csv"
            disabled={busy}
          />
        </label>
        <div className="md:col-span-2">
          <button
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
            type="button"
            onClick={() => void handleUpload()}
            disabled={busy}
          >
            {busy ? 'Working…' : 'Import CSV'}
          </button>
        </div>
      </div>

      {error && (
        <p
          className="rounded-lg bg-red-500/15 px-3 py-2 text-sm text-red-700 dark:text-red-300"
          role="alert"
        >
          {error}
        </p>
      )}
      {message && (
        <p
          className="rounded-lg bg-emerald-500/15 px-3 py-2 text-sm text-emerald-700 dark:text-emerald-300"
          role="status"
        >
          {message}
        </p>
      )}

      {lists.length === 0 ? (
        <p className="text-sm opacity-60">No CSV lists have been imported yet.</p>
      ) : (
        <div className="divide-y divide-black/10 rounded-xl border border-black/10 dark:divide-white/10 dark:border-white/10">
          {lists.map((list) => {
            const isPendingDelete = pendingDeleteId === list.id;
            return (
              <div className="flex items-center justify-between gap-4 p-3" key={list.id}>
                <div className="min-w-0">
                  <strong className="block truncate text-sm">{list.name}</strong>
                  <div className="truncate text-xs opacity-60">
                    {list.book_count.toLocaleString()} books · {list.filename}
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  {isPendingDelete && (
                    <button
                      className="rounded-lg border border-black/15 px-3 py-1.5 text-xs font-medium transition hover:bg-black/5 disabled:cursor-not-allowed disabled:opacity-50 dark:border-white/15 dark:hover:bg-white/5"
                      type="button"
                      onClick={() => {
                        setPendingDeleteId(null);
                        setMessage('');
                      }}
                      disabled={busy}
                    >
                      Cancel
                    </button>
                  )}
                  <button
                    className="rounded-lg border border-red-500/30 px-3 py-1.5 text-xs font-medium text-red-700 transition hover:bg-red-500/10 disabled:cursor-not-allowed disabled:opacity-50 dark:text-red-300"
                    type="button"
                    onClick={() => void handleDelete(list)}
                    disabled={busy}
                    aria-label={`${isPendingDelete ? 'Confirm delete' : 'Delete'} ${list.name}`}
                  >
                    {isPendingDelete ? 'Confirm delete' : 'Delete'}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
};
