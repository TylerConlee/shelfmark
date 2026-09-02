import { describe, expect, it } from 'vitest';

import { transformMetadataToBook } from '../utils/bookTransformers';

describe('metadata library status', () => {
  it('preserves Grimmory presence on transformed search results', () => {
    const book = transformMetadataToBook({
      provider: 'hardcover',
      provider_id: '123',
      title: 'Dune',
      authors: ['Frank Herbert'],
      in_library: true,
      library_book_id: 77,
    });

    expect(book.in_library).toBe(true);
    expect(book.library_book_id).toBe(77);
  });
});
