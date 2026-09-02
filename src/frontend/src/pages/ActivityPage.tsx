import { useMemo } from 'react';

import { ActivityCard } from '../components/activity/ActivityCard';
import type { DownloadStatusKey } from '../components/activity/activityMappers';
import { downloadToActivityItem } from '../components/activity/activityMappers';
import type { ActivityDismissTarget } from '../components/activity/ActivitySidebar';
import type { ActivityItem } from '../components/activity/activityTypes';
import { PageNavigation } from '../components/PageNavigation';
import type { StatusData } from '../types';

interface ActivityPageProps {
  status: StatusData;
  isAdmin: boolean;
  libraryUrl?: string;
  onNavigate: (path: '/' | '/queue' | '/activity') => void;
  onClearCompleted: (items: ActivityDismissTarget[]) => void;
  onCancel: (id: string) => void;
  onRetry: (id: string) => void;
  onDismiss: (id: string) => void;
}

const ACTIVE_STATUSES: DownloadStatusKey[] = ['downloading', 'locating', 'resolving'];
const TERMINAL_STATUSES: DownloadStatusKey[] = ['error', 'cancelled', 'complete'];

export const itemsForStatuses = (status: StatusData, keys: DownloadStatusKey[]): ActivityItem[] =>
  keys
    .flatMap((key) =>
      Object.values(status[key] ?? {}).map((book) => downloadToActivityItem(book, key)),
    )
    .toSorted((left, right) => right.timestamp - left.timestamp);

export const buildClearTargets = (items: ActivityItem[]): ActivityDismissTarget[] =>
  items
    .filter((item) => item.downloadBookId)
    .map((item) => ({
      itemType: 'download' as const,
      itemKey: `download:${item.downloadBookId}`,
    }));

export const ActivityPage = ({
  status,
  isAdmin,
  libraryUrl,
  onNavigate,
  onClearCompleted,
  onCancel,
  onRetry,
  onDismiss,
}: ActivityPageProps) => {
  const activeItems = useMemo(() => itemsForStatuses(status, ACTIVE_STATUSES), [status]);
  const terminalItems = useMemo(() => itemsForStatuses(status, TERMINAL_STATUSES), [status]);
  const clearTargets = useMemo(() => buildClearTargets(terminalItems), [terminalItems]);

  const renderItems = (items: ActivityItem[], emptyMessage: string) =>
    items.length === 0 ? (
      <p className="px-5 py-8 text-center text-sm text-slate-500">{emptyMessage}</p>
    ) : (
      <div className="divide-y divide-(--border-muted) px-4">
        {items.map((item) => (
          <ActivityCard
            key={`${item.visualStatus}:${item.id}`}
            item={item}
            isAdmin={isAdmin}
            onDownloadCancel={onCancel}
            onDownloadRetry={onRetry}
            onDownloadDismiss={onDismiss}
          />
        ))}
      </div>
    );

  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-6 space-y-5">
        <PageNavigation active="activity" onNavigate={onNavigate} libraryUrl={libraryUrl} />
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100">Activity</h1>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
              {activeItems.length === 1
                ? '1 download is in progress'
                : `${activeItems.length} downloads are in progress`}
            </p>
          </div>
          {clearTargets.length > 0 && (
            <button
              type="button"
              onClick={() => onClearCompleted(clearTargets)}
              className="rounded-lg border border-(--border-muted) px-4 py-2 text-sm font-medium text-slate-700 hover:bg-(--hover-surface) dark:text-slate-200"
            >
              Clear Completed Downloads
            </button>
          )}
        </div>
      </div>

      <div className="space-y-6">
        <section className="overflow-hidden rounded-xl border border-(--border-muted) bg-(--bg)">
          <div className="border-b border-(--border-muted) px-5 py-3">
            <h2 className="font-semibold text-slate-900 dark:text-slate-100">Current downloads</h2>
          </div>
          {renderItems(activeItems, 'No downloads are currently running.')}
        </section>

        <section className="overflow-hidden rounded-xl border border-(--border-muted) bg-(--bg)">
          <div className="border-b border-(--border-muted) px-5 py-3">
            <h2 className="font-semibold text-slate-900 dark:text-slate-100">Recent results</h2>
          </div>
          {renderItems(terminalItems, 'No completed, failed, or cancelled downloads.')}
        </section>
      </div>
    </main>
  );
};
