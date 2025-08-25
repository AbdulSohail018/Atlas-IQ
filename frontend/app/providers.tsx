'use client';

import { SWRConfig } from 'swr';
import { api } from '@/lib/api/client';

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <SWRConfig
      value={{
        fetcher: (url: string) => api.get(url).then((res) => res.data),
        revalidateOnFocus: false,
        revalidateOnReconnect: true,
        shouldRetryOnError: (error) => {
          // Retry on network errors but not on 4xx responses
          return error.status >= 500;
        },
        errorRetryCount: 3,
        errorRetryInterval: 1000,
        onError: (error, key) => {
          console.error('SWR Error:', error, 'Key:', key);
        },
      }}
    >
      {children}
    </SWRConfig>
  );
}