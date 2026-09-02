import { formatDistanceToNow, parseISO } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import type { FeedItem, FeedItemType } from '../types';

interface ActivityFeedProps {
  items: FeedItem[];
  loading?: boolean;
}

const TYPE_CONFIG: Record<FeedItemType, { label: string; badge: string; icon: JSX.Element }> = {
  pomodoro: {
    label: 'Pomodoro',
    badge: 'bg-blue-100 text-blue-800',
    icon: (
      <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
  journal: {
    label: 'Journal',
    badge: 'bg-purple-100 text-purple-800',
    icon: (
      <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
      </svg>
    ),
  },
  commit: {
    label: 'Commit',
    badge: 'bg-gray-800 text-white',
    icon: (
      <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
        <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
      </svg>
    ),
  },
};

export default function ActivityFeed({ items, loading }: ActivityFeedProps) {
  if (loading) {
    return (
      <div className="py-8 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-4 border-blue-500 border-t-transparent"></div>
      </div>
    );
  }

  if (!items.length) {
    return (
      <p className="text-gray-500 text-center py-8">
        Nenhuma atividade recente. Complete um Pomodoro ou conecte seu GitHub.
      </p>
    );
  }

  return (
    <ul className="divide-y divide-gray-100">
      {items.map((item, idx) => {
        const config = TYPE_CONFIG[item.type];
        const content = (
          <div className="flex items-start gap-3 py-3">
            <span className={`mt-1 p-1.5 rounded-full shrink-0 ${config.badge}`}>
              {config.icon}
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-gray-900 truncate">{item.title}</p>
              {item.description && (
                <p className="text-sm text-gray-500 line-clamp-2">{item.description}</p>
              )}
              <p className="text-xs text-gray-400 mt-0.5">
                {formatDistanceToNow(parseISO(item.timestamp), { addSuffix: true, locale: ptBR })}
              </p>
            </div>
            <span className={`self-center px-2 py-0.5 text-xs rounded-full shrink-0 ${item.type === 'commit' ? 'bg-gray-100 text-gray-700' : config.badge}`}>
              {config.label}
            </span>
          </div>
        );
        return (
          <li key={`${item.type}-${item.timestamp}-${idx}`}>
            {item.url ? (
              <a href={item.url} target="_blank" rel="noopener noreferrer" className="block hover:bg-gray-50 rounded-lg">
                {content}
              </a>
            ) : (
              content
            )}
          </li>
        );
      })}
    </ul>
  );
}
