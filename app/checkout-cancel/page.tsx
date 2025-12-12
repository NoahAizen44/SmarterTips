'use client';

import { useRouter } from 'next/navigation';
import { useAuth } from '@/app/lib/auth-context';
import { useEffect } from 'react';
import Link from 'next/link';

export default function CheckoutCancelPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login');
    }
  }, [user, authLoading, router]);

  if (authLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center">
        <p className="text-slate-400">Loading...</p>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center px-4">
      <div className="max-w-md w-full">
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-8 text-center">
          {/* Error icon */}
          <div className="mb-6 flex justify-center">
            <div className="w-16 h-16 bg-amber-500/20 rounded-full flex items-center justify-center">
              <svg
                className="w-8 h-8 text-amber-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </div>
          </div>

          <h1 className="text-3xl font-bold text-white mb-3">
            Checkout Cancelled
          </h1>

          <p className="text-slate-400 mb-2">
            Your upgrade to Premium was cancelled.
          </p>

          <p className="text-slate-500 text-sm mb-8">
            No charge was made to your account. You can try again whenever you're ready.
          </p>

          <div className="space-y-3">
            <Link
              href="/pricing"
              className="block w-full py-3 px-6 bg-gradient-to-r from-amber-500 to-orange-500 text-white font-semibold rounded-lg hover:from-amber-600 hover:to-orange-600 transition-all"
            >
              Try Again
            </Link>

            <Link
              href="/app"
              className="block w-full py-3 px-6 border border-slate-600 text-slate-300 font-semibold rounded-lg hover:bg-slate-700 transition-colors"
            >
              Back to Dashboard
            </Link>
          </div>

          <p className="text-slate-500 text-xs mt-6">
            Need help?{' '}
            <a href="mailto:support@smartertips.com" className="text-slate-300 hover:text-white">
              Contact support
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
