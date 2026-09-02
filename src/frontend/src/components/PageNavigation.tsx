interface PageNavigationProps {
  active: 'search' | 'queue' | 'activity';
  onNavigate: (path: '/' | '/queue' | '/activity') => void;
  libraryUrl?: string;
}

const links: Array<{
  key: PageNavigationProps['active'];
  label: string;
  path: '/' | '/queue' | '/activity';
}> = [
  { key: 'search', label: 'Search', path: '/' },
  { key: 'queue', label: 'Queue', path: '/queue' },
  { key: 'activity', label: 'Activity', path: '/activity' },
];

export const PageNavigation = ({ active, onNavigate, libraryUrl }: PageNavigationProps) => (
  <nav aria-label="Shelfmark" className="flex flex-wrap items-center gap-2">
    {links.map((link) => (
      <button
        key={link.key}
        type="button"
        onClick={() => onNavigate(link.path)}
        aria-current={active === link.key ? 'page' : undefined}
        className={`rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
          active === link.key
            ? 'bg-sky-600 text-white'
            : 'hover-action text-slate-700 dark:text-slate-200'
        }`}
      >
        {link.label}
      </button>
    ))}
    {libraryUrl && (
      <a
        href={libraryUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="hover-action rounded-lg px-3 py-2 text-sm font-medium text-slate-700 dark:text-slate-200"
      >
        Library
      </a>
    )}
  </nav>
);
