'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  ChartBarIcon,
  ChatBubbleLeftRightIcon,
  MapIcon,
  ClockIcon,
  DocumentTextIcon,
  ArrowTrendingUpIcon,
  GlobeAltIcon,
  UsersIcon,
} from '@heroicons/react/24/outline';
import Link from 'next/link';
import { QuickQueryCard } from '@/components/chat/QuickQueryCard';
import { StatsCard } from '@/components/ui/StatsCard';
import { RecentActivity } from '@/components/ui/RecentActivity';
import { DatasetOverview } from '@/components/datasets/DatasetOverview';

const stats = [
  {
    name: 'Total Datasets',
    value: '2,847',
    change: '+12%',
    changeType: 'increase' as const,
    icon: DocumentTextIcon,
  },
  {
    name: 'Queries Processed',
    value: '18.2K',
    change: '+24%',
    changeType: 'increase' as const,
    icon: ChatBubbleLeftRightIcon,
  },
  {
    name: 'Active Sources',
    value: '156',
    change: '+3%',
    changeType: 'increase' as const,
    icon: GlobeAltIcon,
  },
  {
    name: 'Knowledge Entities',
    value: '94.3K',
    change: '+18%',
    changeType: 'increase' as const,
    icon: UsersIcon,
  },
];

const quickActions = [
  {
    name: 'Start Conversation',
    description: 'Ask questions about policies and data',
    href: '/chat',
    icon: ChatBubbleLeftRightIcon,
    color: 'bg-blue-500',
  },
  {
    name: 'Explore Map',
    description: 'View data geographically',
    href: '/map',
    icon: MapIcon,
    color: 'bg-green-500',
  },
  {
    name: 'Browse Timeline',
    description: 'Explore historical trends',
    href: '/timeline',
    icon: ClockIcon,
    color: 'bg-purple-500',
  },
  {
    name: 'View Analytics',
    description: 'Deep dive into data patterns',
    href: '/analytics',
    icon: ChartBarIcon,
    color: 'bg-orange-500',
  },
];

const sampleQueries = [
  {
    id: 'q1',
    question: 'What are the air quality trends in major cities?',
    category: 'Environment',
    description: 'Analyze air quality data across metropolitan areas',
    suggested_mode: 'analyst' as const,
  },
  {
    id: 'q2',
    question: 'How do climate policies compare between EU and US?',
    category: 'Policy',
    description: 'Compare climate legislation and regulations',
    suggested_mode: 'researcher' as const,
  },
  {
    id: 'q3',
    question: 'What services can I request through 311 in my area?',
    category: 'Civic',
    description: 'Learn about local government services',
    suggested_mode: 'citizen' as const,
  },
];

export function DashboardView() {
  const [selectedTimeRange, setSelectedTimeRange] = useState('7d');

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="px-4 sm:px-6 lg:px-8 py-8">
          <div className="md:flex md:items-center md:justify-between">
            <div className="min-w-0 flex-1">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
              >
                <h1 className="text-3xl font-bold text-gray-900 gradient-text">
                  Welcome to Glonav
                </h1>
                <p className="mt-2 text-lg text-gray-600">
                  Navigate global policies and public data with AI-powered insights
                </p>
              </motion.div>
            </div>
            <div className="mt-4 flex md:ml-4 md:mt-0">
              <select
                value={selectedTimeRange}
                onChange={(e) => setSelectedTimeRange(e.target_value)}
                className="form-select"
              >
                <option value="24h">Last 24 hours</option>
                <option value="7d">Last 7 days</option>
                <option value="30d">Last 30 days</option>
                <option value="90d">Last 90 days</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      <div className="px-4 sm:px-6 lg:px-8 py-8">
        {/* Stats Grid */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4 mb-8"
        >
          {stats.map((stat, index) => (
            <motion.div
              key={stat.name}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.1 * index }}
            >
              <StatsCard {...stat} />
            </motion.div>
          ))}
        </motion.div>

        {/* Quick Actions */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.4 }}
          className="mb-8"
        >
          <h2 className="text-xl font-semibold text-gray-900 mb-6">Quick Actions</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {quickActions.map((action, index) => (
              <motion.div
                key={action.name}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.1 * index }}
              >
                <Link
                  href={action.href}
                  className="group relative overflow-hidden rounded-xl bg-white p-6 shadow-sm border border-gray-200 hover:shadow-md transition-all duration-200"
                >
                  <div className="flex items-center">
                    <div className={`flex h-12 w-12 items-center justify-center rounded-lg ${action.color}`}>
                      <action.icon className="h-6 w-6 text-white" />
                    </div>
                    <div className="ml-4 flex-1">
                      <h3 className="text-lg font-medium text-gray-900 group-hover:text-primary-600 transition-colors">
                        {action.name}
                      </h3>
                      <p className="text-sm text-gray-500">{action.description}</p>
                    </div>
                  </div>
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent to-primary-50 opacity-0 group-hover:opacity-100 transition-opacity duration-200" />
                </Link>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Sample Queries */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6, delay: 0.6 }}
            className="lg:col-span-2"
          >
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-semibold text-gray-900">
                  Popular Questions
                </h2>
                <Link
                  href="/chat"
                  className="text-sm font-medium text-primary-600 hover:text-primary-700"
                >
                  View all →
                </Link>
              </div>
              <div className="space-y-4">
                {sampleQueries.map((query, index) => (
                  <motion.div
                    key={query.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.4, delay: 0.1 * index }}
                  >
                    <QuickQueryCard query={query} />
                  </motion.div>
                ))}
              </div>
            </div>
          </motion.div>

          {/* Right Sidebar */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6, delay: 0.8 }}
            className="space-y-6"
          >
            {/* Recent Activity */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                Recent Activity
              </h3>
              <RecentActivity />
            </div>

            {/* System Status */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                System Status
              </h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">API Services</span>
                  <div className="flex items-center space-x-2">
                    <div className="h-2 w-2 bg-green-400 rounded-full"></div>
                    <span className="text-sm text-green-600">Operational</span>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Knowledge Graph</span>
                  <div className="flex items-center space-x-2">
                    <div className="h-2 w-2 bg-green-400 rounded-full"></div>
                    <span className="text-sm text-green-600">Operational</span>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Data Pipeline</span>
                  <div className="flex items-center space-x-2">
                    <div className="h-2 w-2 bg-yellow-400 rounded-full"></div>
                    <span className="text-sm text-yellow-600">Processing</span>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">AI Models</span>
                  <div className="flex items-center space-x-2">
                    <div className="h-2 w-2 bg-green-400 rounded-full"></div>
                    <span className="text-sm text-green-600">Operational</span>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        </div>

        {/* Dataset Overview */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 1.0 }}
          className="mt-8"
        >
          <DatasetOverview />
        </motion.div>
      </div>
    </div>
  );
}