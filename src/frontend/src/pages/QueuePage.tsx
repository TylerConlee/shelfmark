import { useCallback, useState } from 'react';

import { PageNavigation } from '../components/PageNavigation';
import { useMountEffect } from '../hooks/useMountEffect';
import { cancelDownload, getQueueOrder, type QueueOrderItem } from '../services/api';

interface QueuePageProps {
  onNavigate: (path: '/' | '/queue' | '/activity') => void;
  libraryUrl?: string;
  onQueueChanged?: () => Promise<void> | void;
}

const formatQueuedTime = (timestamp: number): string => {
  if (!Number.isFinite(timestamp) || timestamp <= 0) return 'Unknown';
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(timestamp * 1000));
};

export const QueuePage = ({ onNavigate, libraryUrl, onQueueChanged }: QueuePageProps) => {
  const [items, setItems] = useState<QueueOrderItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cancellingId, setCancellingId] = useState<string | null>(null);

  const loadQueue = useCallback(async () => {
    try {
      const queue = await getQueueOrder();
      setItems(queue);
      setError(null);
    } catch (loadError) {
      console.error('Failed to load queue:', loadError);
      setError('The queue could not be loaded.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useMountEffect(() => {
    void loadQueue();
    const timer = window.setInterval(() => void loadQueue(), 5000);
    return () => window.clearInterval(timer);
  });

  const handleCancel = async (item: QueueOrderItem) => {
    setCancellingId(item.id);
    try {
      await cancelDownload(item.id);
      await loadQueue();
      await onQueueChanged?.();
    } catch (cancelError) {
      console.error('Failed to cancel queued download:', cancelError);
      setError(`Could not remove “${item.title || 'Untitled'}” from the queue.`);
    } finally {
      setCancellingId(null);
    }
  };

  const emptyQueue = (
    <div className="px-6 py-12 text-center">
      <h2 className="font-medium text-slate-900 dark:text-slate-100">The queue is empty</h2>
      <p className="mt-1 text-sm text-slate-500">New downloads will appear here while they wait.</p>
    </div>
  );

  let queueContent = emptyQueue;
  if (isLoading && items.length === 0) {
    queueContent = <p className="px-6 py-12 text-center text-slate-500">Loading queued books…</p>;
  } else if (items.length > 0) {
    queueContent = (
      <ol className="divide-y divide-(--border-muted)">
        {items.map((item, index) => (
          <li key={item.id} className="flex items-center gap-4 px-4 py-4 sm:px-6">
            <span className="w-8 shrink-0 text-center text-sm font-semibold text-slate-500">
              {index + 1}
            </span>
            <div className="min-w-0 flex-1">
              <h2 className="truncate font-medium text-slate-900 dark:text-slate-100">
                {item.title || 'Untitled'}
              </h2>
              <p className="mt-1 truncate text-sm text-slate-600 dark:text-slate-400">
                {item.author || 'Unknown author'}
              </p>
              <p className="mt-1 text-xs text-slate-500">
                {item.source === 'csv' && item.csv_list_name
                  ? `Queued from ${item.csv_list_name}`
                  : `Queued ${formatQueuedTime(item.added_time)}`}
              </p>
            </div>
            {item.removable !== false && (
              <button
                type="button"
                onClick={() => void handleCancel(item)}
                disabled={cancellingId === item.id}
                className="hover-action shrink-0 rounded-lg px-3 py-2 text-sm font-medium text-red-600 disabled:opacity-50 dark:text-red-400"
                aria-label={`Remove ${item.title || 'Untitled'} from queue`}
              >
                {cancellingId === item.id ? 'Removing…' : 'Remove'}
              </button>
            )}
          </li>
        ))}
      </ol>
    );
  }

  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <PageNavigation active="queue" onNavigate={onNavigate} libraryUrl={libraryUrl} />
          <h1 className="mt-5 text-2xl font-semibold text-slate-900 dark:text-slate-100">
            Download queue
          </h1>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
            {items.length === 1 ? '1 book is waiting' : `${items.length} books are waiting`}
          </p>
        </div>
        <button
          type="button"
          onClick={() => void loadQueue()}
          disabled={isLoading}
          className="hover-action rounded-lg px-4 py-2 text-sm font-medium disabled:opacity-50"
        >
          Refresh
        </button>
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200">
          {error}
        </div>
      )}

      <section className="overflow-hidden rounded-xl border border-(--border-muted) bg-(--bg)">
        {queueContent}
      </section>
    </main>
  );
};
