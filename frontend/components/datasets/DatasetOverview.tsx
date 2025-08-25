'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  DocumentTextIcon,
  GlobeAltIcon,
  ChartBarIcon,
  CalendarIcon,
  TagIcon,
  ArrowRightIcon,
} from '@heroicons/react/24/outline';
import { clsx } from 'clsx';
import Link from 'next/link';

interface Dataset {
  id: string;
  name: string;
  description: string;
  source: string;
  record_count: number;
  last_updated: string;
  tags: string[];
  category: string;
}

const mockDatasets: Dataset[] = [
  {
    id: '1',
    name: 'NYC 311 Service Requests',
    description: 'Service requests from NYC 311 system including complaints, inquiries, and service requests',
    source: 'NYC Open Data',
    record_count: 2847592,
    last_updated: '2024-01-15T10:30:00Z',
    tags: ['311', 'nyc', 'services', 'complaints'],
    category: 'Civic',
  },
  {
    id: '2',
    name: 'EPA Air Quality Index',
    description: 'Daily air quality measurements from EPA monitoring stations across the US',
    source: 'EPA',
    record_count: 1253847,
    last_updated: '2024-01-15T08:00:00Z',
    tags: ['air quality', 'environment', 'epa', 'pollution'],
    category: 'Environment',
  },
  {
    id: '3',
    name: 'US Census Demographics',
    description: 'Population and demographic data from US Census Bureau',
    source: 'US Census Bureau',
    record_count: 895231,
    last_updated: '2024-01-14T16:45:00Z',
    tags: ['demographics', 'population', 'census'],
    category: 'Demographics',
  },
  {
    id: '4',
    name: 'WHO Global Health Data',
    description: 'Health statistics and indicators from World Health Organization',
    source: 'WHO',
    record_count: 567432,
    last_updated: '2024-01-14T12:20:00Z',
    tags: ['health', 'global', 'who', 'statistics'],
    category: 'Health',
  },
  {
    id: '5',
    name: 'Climate Change Indicators',
    description: 'Long-term climate data and change indicators',
    source: 'NOAA',
    record_count: 423156,
    last_updated: '2024-01-13T09:15:00Z',
    tags: ['climate', 'weather', 'temperature', 'environment'],
    category: 'Environment',
  },
];

const categoryColors = {
  Civic: 'bg-blue-100 text-blue-800',
  Environment: 'bg-green-100 text-green-800',
  Demographics: 'bg-purple-100 text-purple-800',
  Health: 'bg-red-100 text-red-800',
  Policy: 'bg-orange-100 text-orange-800',
};

export function DatasetOverview() {
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  
  const categories = ['All', ...Array.from(new Set(mockDatasets.map(d => d.category)))];
  
  const filteredDatasets = selectedCategory === 'All' 
    ? mockDatasets 
    : mockDatasets.filter(d => d.category === selectedCategory);

  const formatNumber = (num: number): string => {
    if (num >= 1000000) {
      return `${(num / 1000000).toFixed(1)}M`;
    } else if (num >= 1000) {
      return `${(num / 1000).toFixed(1)}K`;
    }
    return num.toString();
  };

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">Available Datasets</h2>
          <p className="text-sm text-gray-600 mt-1">
            Explore our collection of public data sources
          </p>
        </div>
        <Link
          href="/datasets"
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-lg text-primary-600 bg-primary-50 hover:bg-primary-100 transition-colors"
        >
          View all datasets
          <ArrowRightIcon className="ml-2 h-4 w-4" />
        </Link>
      </div>

      {/* Category filter */}
      <div className="flex flex-wrap gap-2 mb-6">
        {categories.map((category) => (
          <button
            key={category}
            onClick={() => setSelectedCategory(category)}
            className={clsx(
              'px-3 py-1 text-sm font-medium rounded-full transition-colors',
              selectedCategory === category
                ? 'bg-primary-100 text-primary-800 border border-primary-200'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200 border border-transparent'
            )}
          >
            {category}
          </button>
        ))}
      </div>

      {/* Dataset grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredDatasets.map((dataset, index) => (
          <motion.div
            key={dataset.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: index * 0.1 }}
          >
            <DatasetCard dataset={dataset} />
          </motion.div>
        ))}
      </div>

      {filteredDatasets.length === 0 && (
        <div className="text-center py-8">
          <DocumentTextIcon className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">No datasets found</h3>
          <p className="mt-1 text-sm text-gray-500">
            Try selecting a different category
          </p>
        </div>
      )}
    </div>
  );
}

function DatasetCard({ dataset }: { dataset: Dataset }) {
  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      className="group relative overflow-hidden rounded-lg border border-gray-200 bg-gray-50 p-4 hover:border-primary-300 hover:shadow-md transition-all duration-200"
    >
      {/* Background gradient on hover */}
      <div className="absolute inset-0 bg-gradient-to-br from-white to-gray-50 group-hover:from-primary-50 group-hover:to-white transition-all duration-200" />
      
      {/* Content */}
      <div className="relative">
        {/* Header */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1">
            <div className="flex items-center space-x-2 mb-2">
              <span className={clsx(
                'inline-flex items-center rounded-full px-2 py-1 text-xs font-medium',
                categoryColors[dataset.category as keyof typeof categoryColors] || 'bg-gray-100 text-gray-800'
              )}>
                {dataset.category}
              </span>
            </div>
            <h3 className="text-sm font-semibold text-gray-900 group-hover:text-primary-700 transition-colors line-clamp-2">
              {dataset.name}
            </h3>
          </div>
          <DocumentTextIcon className="h-5 w-5 text-gray-400 group-hover:text-primary-600 transition-colors flex-shrink-0 ml-2" />
        </div>

        {/* Description */}
        <p className="text-xs text-gray-600 mb-3 line-clamp-2">
          {dataset.description}
        </p>

        {/* Metadata */}
        <div className="space-y-2 mb-3">
          <div className="flex items-center text-xs text-gray-500">
            <GlobeAltIcon className="h-3 w-3 mr-1 flex-shrink-0" />
            <span className="truncate">{dataset.source}</span>
          </div>
          <div className="flex items-center text-xs text-gray-500">
            <ChartBarIcon className="h-3 w-3 mr-1 flex-shrink-0" />
            <span>{formatNumber(dataset.record_count)} records</span>
          </div>
          <div className="flex items-center text-xs text-gray-500">
            <CalendarIcon className="h-3 w-3 mr-1 flex-shrink-0" />
            <span>Updated {formatDate(dataset.last_updated)}</span>
          </div>
        </div>

        {/* Tags */}
        <div className="flex flex-wrap gap-1">
          {dataset.tags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="inline-flex items-center rounded px-2 py-0.5 text-xs font-medium bg-gray-100 text-gray-700"
            >
              {tag}
            </span>
          ))}
          {dataset.tags.length > 3 && (
            <span className="inline-flex items-center rounded px-2 py-0.5 text-xs font-medium bg-gray-100 text-gray-700">
              +{dataset.tags.length - 3}
            </span>
          )}
        </div>
      </div>
    </motion.div>
  );
}

function formatNumber(num: number): string {
  if (num >= 1000000) {
    return `${(num / 1000000).toFixed(1)}M`;
  } else if (num >= 1000) {
    return `${(num / 1000).toFixed(1)}K`;
  }
  return num.toString();
}

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}