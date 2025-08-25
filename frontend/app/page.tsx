import { Suspense } from 'react';
import { MainLayout } from '@/components/layout/MainLayout';
import { DashboardView } from '@/components/layout/DashboardView';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

export default function HomePage() {
  return (
    <MainLayout>
      <Suspense fallback={<LoadingSpinner />}>
        <DashboardView />
      </Suspense>
    </MainLayout>
  );
}