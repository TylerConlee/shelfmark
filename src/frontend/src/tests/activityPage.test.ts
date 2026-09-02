import { describe, expect, it } from 'vitest';

import { buildClearTargets, itemsForStatuses } from '../pages/ActivityPage';
import type { StatusData } from '../types';

const status = {
  downloading: {
    live: { id: 'live', title: 'Live book', author: 'Author', added_time: 2 },
  },
  error: {
    failed: {
      id: 'failed',
      title: 'Failed book',
      author: 'Author',
      status_message: 'Provider returned no downloadable files',
      added_time: 3,
    },
  },
  complete: {
    done: { id: 'done', title: 'Done book', author: 'Author', added_time: 1 },
  },
} as StatusData;

describe('ActivityPage helpers', () => {
  it('separates current downloads from terminal results and preserves failure details', () => {
    const current = itemsForStatuses(status, ['downloading', 'queued']);
    const terminal = itemsForStatuses(status, ['error', 'cancelled', 'complete']);

    expect(current.map((item) => item.id)).toEqual(['live']);
    expect(terminal.map((item) => item.id)).toEqual(['failed', 'done']);
    expect(terminal[0].statusDetail).toBe('Provider returned no downloadable files');
  });

  it('builds clear targets for every visible terminal download', () => {
    const terminal = itemsForStatuses(status, ['error', 'cancelled', 'complete']);

    expect(buildClearTargets(terminal)).toEqual([
      { itemType: 'download', itemKey: 'download:failed' },
      { itemType: 'download', itemKey: 'download:done' },
    ]);
  });
});
