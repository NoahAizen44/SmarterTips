'use client';

import { useAuth } from '@/app/lib/auth-context';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { ReactNode } from 'react';

interface ProtectedToolWrapperProps {
  children: ReactNode;
  toolName: string;
  toolDescription: string;
}

export default function ProtectedToolWrapper({
  children,
  toolName,
  toolDescription,
}: ProtectedToolWrapperProps) {
  const router = useRouter();
  const { profile, loading } = useAuth();

  // Still loading
  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center">
        <p className="text-slate-400">Loading...</p>
      </div>
    );
  }

  // User is not premium
  if (profile?.subscription_tier === 'free') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
        <div className="max-w-md w-full">
          <div className="bg-slate-800 border border-slate-700 rounded-lg shadow-xl p-8 text-center">
            {/* Lock icon */}
            <div className="mb-6 flex justify-center">
              <div className="w-16 h-16 bg-amber-500/20 rounded-full flex items-center justify-center">
                <svg
                  className="w-8 h-8 text-amber-400"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z"
                    clipRule="evenodd"
                  />
                </svg>
              </div>
            </div>

            <h1 className="text-2xl font-bold text-white mb-2">
              Premium Feature
            </h1>

            <p className="text-slate-400 mb-3">
              {toolName}
            </p>

            <p className="text-slate-500 text-sm mb-8">
              {toolDescription}
            </p>

            <p className="text-amber-400 font-semibold mb-6">
              Upgrade to Premium for just $9.99/month
            </p>

            <div className="space-y-3">
              <Link
                href="/pricing"
                className="block w-full py-3 px-6 bg-gradient-to-r from-amber-500 to-orange-500 text-white font-semibold rounded-lg hover:from-amber-600 hover:to-orange-600 transition-all"
              >
                Upgrade to Premium
              </Link>

              <Link
                href="/"
                className="block w-full py-3 px-6 border border-slate-600 text-slate-300 font-semibold rounded-lg hover:bg-slate-700 transition-colors"
              >
                Back to Dashboard
              </Link>
            </div>

            <p className="text-slate-600 text-xs mt-6">
              Premium unlocks all advanced tools and removes ads
            </p>
          </div>
        </div>
      </div>
    );
  }

  // User is premium or loading completed - show content
  return <>{children}</>;
}
