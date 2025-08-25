'use client';

import { motion } from 'framer-motion';
import { clsx } from 'clsx';
import { ArrowTrendingUpIcon, ArrowTrendingDownIcon } from '@heroicons/react/24/outline';

interface StatsCardProps {
  name: string;
  value: string;
  change: string;
  changeType: 'increase' | 'decrease' | 'neutral';
  icon: React.ComponentType<{ className?: string }>;
}

export function StatsCard({ name, value, change, changeType, icon: Icon }: StatsCardProps) {
  const changeColor = {
    increase: 'text-green-600',
    decrease: 'text-red-600',
    neutral: 'text-gray-600',
  };

  const changeBgColor = {
    increase: 'bg-green-50',
    decrease: 'bg-red-50',
    neutral: 'bg-gray-50',
  };

  const TrendIcon = changeType === 'increase' ? ArrowTrendingUpIcon : 
                   changeType === 'decrease' ? ArrowTrendingDownIcon : null;

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow duration-200"
    >
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <Icon className="h-8 w-8 text-primary-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">{name}</p>
              <p className="text-2xl font-bold text-gray-900">{value}</p>
            </div>
          </div>
        </div>
        <div className={clsx(
          'flex items-center rounded-full px-2.5 py-1 text-sm font-medium',
          changeBgColor[changeType]
        )}>
          {TrendIcon && (
            <TrendIcon className={clsx('h-4 w-4 mr-1', changeColor[changeType])} />
          )}
          <span className={changeColor[changeType]}>{change}</span>
        </div>
      </div>
    </motion.div>
  );
}