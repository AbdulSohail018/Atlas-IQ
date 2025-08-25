'use client';

import { motion } from 'framer-motion';
import { 
  ChatBubbleLeftRightIcon,
  ArrowRightIcon,
  TagIcon
} from '@heroicons/react/24/outline';
import { clsx } from 'clsx';
import Link from 'next/link';

interface QuickQuery {
  id: string;
  question: string;
  category: string;
  description: string;
  suggested_mode: 'analyst' | 'researcher' | 'citizen';
}

interface QuickQueryCardProps {
  query: QuickQuery;
  onClick?: () => void;
}

const modeColors = {
  analyst: 'bg-blue-100 text-blue-800',
  researcher: 'bg-purple-100 text-purple-800',
  citizen: 'bg-green-100 text-green-800',
};

const categoryColors = {
  Environment: 'bg-green-50 text-green-700 border-green-200',
  Policy: 'bg-blue-50 text-blue-700 border-blue-200',
  Civic: 'bg-orange-50 text-orange-700 border-orange-200',
  Health: 'bg-red-50 text-red-700 border-red-200',
  Demographics: 'bg-purple-50 text-purple-700 border-purple-200',
};

export function QuickQueryCard({ query, onClick }: QuickQueryCardProps) {
  const categoryColor = categoryColors[query.category as keyof typeof categoryColors] || 'bg-gray-50 text-gray-700 border-gray-200';
  
  const handleClick = () => {
    if (onClick) {
      onClick();
    } else {
      // Navigate to chat with pre-filled query
      const encodedQuery = encodeURIComponent(query.question);
      const mode = query.suggested_mode;
      window.location.href = `/chat?q=${encodedQuery}&mode=${mode}`;
    }
  };

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      className="group relative overflow-hidden rounded-lg border border-gray-200 bg-white p-4 hover:border-primary-300 hover:shadow-md transition-all duration-200 cursor-pointer"
      onClick={handleClick}
    >
      {/* Background gradient on hover */}
      <div className="absolute inset-0 bg-gradient-to-r from-primary-50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-200" />
      
      {/* Content */}
      <div className="relative">
        {/* Header */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center space-x-2">
            <div className="flex-shrink-0">
              <ChatBubbleLeftRightIcon className="h-5 w-5 text-primary-600" />
            </div>
            <div className="flex items-center space-x-2">
              <span className={clsx(
                'inline-flex items-center rounded-full px-2 py-1 text-xs font-medium border',
                categoryColor
              )}>
                <TagIcon className="h-3 w-3 mr-1" />
                {query.category}
              </span>
              <span className={clsx(
                'inline-flex items-center rounded-full px-2 py-1 text-xs font-medium',
                modeColors[query.suggested_mode]
              )}>
                {query.suggested_mode}
              </span>
            </div>
          </div>
          <ArrowRightIcon className="h-4 w-4 text-gray-400 group-hover:text-primary-600 transition-colors" />
        </div>

        {/* Question */}
        <h3 className="text-sm font-medium text-gray-900 group-hover:text-primary-700 transition-colors mb-2">
          {query.question}
        </h3>

        {/* Description */}
        <p className="text-sm text-gray-600 line-clamp-2">
          {query.description}
        </p>

        {/* Action hint */}
        <div className="mt-3 flex items-center text-xs text-gray-500 group-hover:text-primary-600 transition-colors">
          <span>Click to start conversation</span>
        </div>
      </div>
    </motion.div>
  );
}

interface QuickQueryListProps {
  queries: QuickQuery[];
  onQuerySelect?: (query: QuickQuery) => void;
  className?: string;
}

export function QuickQueryList({ queries, onQuerySelect, className }: QuickQueryListProps) {
  return (
    <div className={clsx('space-y-3', className)}>
      {queries.map((query, index) => (
        <motion.div
          key={query.id}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: index * 0.1 }}
        >
          <QuickQueryCard 
            query={query} 
            onClick={() => onQuerySelect?.(query)} 
          />
        </motion.div>
      ))}
    </div>
  );
}