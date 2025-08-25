'use client';

import { motion } from 'framer-motion';
import { 
  ChatBubbleLeftRightIcon,
  DocumentTextIcon,
  ChartBarIcon,
  MapIcon,
  ClockIcon
} from '@heroicons/react/24/outline';
import { clsx } from 'clsx';

interface ActivityItem {
  id: string;
  type: 'query' | 'dataset' | 'analysis' | 'exploration';
  title: string;
  description: string;
  timestamp: string;
  status: 'completed' | 'processing' | 'failed';
}

const mockActivities: ActivityItem[] = [
  {
    id: '1',
    type: 'query',
    title: 'Air Quality Analysis',
    description: 'Analyzed pollution trends in 15 major cities',
    timestamp: '2 minutes ago',
    status: 'completed',
  },
  {
    id: '2',
    type: 'dataset',
    title: 'WHO Health Data',
    description: 'Updated global health indicators dataset',
    timestamp: '1 hour ago',
    status: 'processing',
  },
  {
    id: '3',
    type: 'analysis',
    title: 'Policy Comparison',
    description: 'Compared climate policies across EU countries',
    timestamp: '3 hours ago',
    status: 'completed',
  },
  {
    id: '4',
    type: 'exploration',
    title: 'Map Exploration',
    description: 'Explored demographic data in urban areas',
    timestamp: '5 hours ago',
    status: 'completed',
  },
  {
    id: '5',
    type: 'query',
    title: '311 Services Query',
    description: 'Asked about available civic services',
    timestamp: '1 day ago',
    status: 'failed',
  },
];

const iconMap = {
  query: ChatBubbleLeftRightIcon,
  dataset: DocumentTextIcon,
  analysis: ChartBarIcon,
  exploration: MapIcon,
};

const statusColors = {
  completed: 'bg-green-100 text-green-800',
  processing: 'bg-yellow-100 text-yellow-800',
  failed: 'bg-red-100 text-red-800',
};

const typeColors = {
  query: 'bg-blue-100 text-blue-600',
  dataset: 'bg-green-100 text-green-600',
  analysis: 'bg-purple-100 text-purple-600',
  exploration: 'bg-orange-100 text-orange-600',
};

export function RecentActivity() {
  return (
    <div className="flow-root">
      <ul className="-mb-8">
        {mockActivities.map((activity, index) => {
          const Icon = iconMap[activity.type];
          const isLast = index === mockActivities.length - 1;
          
          return (
            <motion.li
              key={activity.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3, delay: index * 0.1 }}
            >
              <div className="relative pb-8">
                {!isLast && (
                  <span
                    className="absolute left-4 top-8 -ml-px h-full w-0.5 bg-gray-200"
                    aria-hidden="true"
                  />
                )}
                <div className="relative flex space-x-3">
                  <div>
                    <span className={clsx(
                      'h-8 w-8 rounded-full flex items-center justify-center ring-8 ring-white',
                      typeColors[activity.type]
                    )}>
                      <Icon className="h-4 w-4" />
                    </span>
                  </div>
                  <div className="flex min-w-0 flex-1 justify-between space-x-4">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center space-x-2">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {activity.title}
                        </p>
                        <span className={clsx(
                          'inline-flex items-center rounded-full px-2 py-1 text-xs font-medium',
                          statusColors[activity.status]
                        )}>
                          {activity.status}
                        </span>
                      </div>
                      <p className="text-sm text-gray-500 mt-1">
                        {activity.description}
                      </p>
                    </div>
                    <div className="whitespace-nowrap text-right text-sm text-gray-500">
                      <ClockIcon className="inline h-4 w-4 mr-1" />
                      {activity.timestamp}
                    </div>
                  </div>
                </div>
              </div>
            </motion.li>
          );
        })}
      </ul>
    </div>
  );
}