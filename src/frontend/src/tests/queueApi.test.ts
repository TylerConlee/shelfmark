import { afterEach, describe, expect, it, vi } from 'vitest';

import { getQueueOrder } from '../services/api';

describe('getQueueOrder', () => {
  afterEach(() => vi.restoreAllMocks());

  it('returns every ordered queued item from the API', async () => {
    const queue = [
      {
        id: 'csv-1',
        title: 'First',
        author: 'Author A',
        priority: 10,
        added_time: 1,
        status: 'queued',
      },
      {
        id: 'csv-2',
        title: 'Second',
        author: 'Author B',
        priority: 10,
        added_time: 2,
        status: 'queued',
      },
    ];
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ queue }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    await expect(getQueueOrder()).resolves.toEqual(queue);
  });

  it('uses an empty list when the response has no queue array', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({}), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    await expect(getQueueOrder()).resolves.toEqual([]);
  });
});
