import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import { Toaster } from 'react-hot-toast';
import '../styles/globals.css';
import { Providers } from './providers';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Glonav - Global Policy & Knowledge Navigator',
  description: 'Navigate global policies and public data with AI-powered insights',
  keywords: ['policy', 'data', 'AI', 'knowledge graph', 'analytics'],
  authors: [{ name: 'Glonav Team' }],
  viewport: {
    width: 'device-width',
    initialScale: 1,
    maximumScale: 1,
  },
  themeColor: '#3b82f6',
  openGraph: {
    title: 'Glonav - Global Policy & Knowledge Navigator',
    description: 'Navigate global policies and public data with AI-powered insights',
    type: 'website',
    locale: 'en_US',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Glonav - Global Policy & Knowledge Navigator',
    description: 'Navigate global policies and public data with AI-powered insights',
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full">
      <body className={`${inter.className} h-full bg-gray-50 antialiased`}>
        <Providers>
          {children}
          <Toaster
            position="top-right"
            toastOptions={{
              duration: 4000,
              style: {
                background: '#374151',
                color: '#f9fafb',
                borderRadius: '0.75rem',
                border: '1px solid #4b5563',
              },
              success: {
                iconTheme: {
                  primary: '#10b981',
                  secondary: '#f9fafb',
                },
              },
              error: {
                iconTheme: {
                  primary: '#ef4444',
                  secondary: '#f9fafb',
                },
              },
            }}
          />
        </Providers>
      </body>
    </html>
  );
}