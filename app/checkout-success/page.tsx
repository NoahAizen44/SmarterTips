'use client';

import { useRouter } from 'next/navigation';
import { useAuth } from '@/app/lib/auth-context';
import { useEffect, Suspense } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';

function CheckoutSuccessContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, loading: authLoading } = useAuth();
  const sessionId = searchParams.get('session_id');

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
          {/* Success icon */}
          <div className="mb-6 flex justify-center">
            <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center">
              <svg
                className="w-8 h-8 text-green-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
            </div>
          </div>

          <h1 className="text-3xl font-bold text-white mb-3">
            Welcome to Premium!
          </h1>

          <p className="text-slate-400 mb-2">
            Thank you for upgrading to SmarterTips Premium.
          </p>

          <p className="text-slate-500 text-sm mb-8">
            Your subscription is now active. You have full access to all premium tools and features.
          </p>

          {sessionId && (
            <p className="text-slate-600 text-xs mb-6">
              Session ID: {sessionId.substring(0, 20)}...
            </p>
          )}

          <div className="space-y-3">
            <Link
              href="/app"
              className="block w-full py-3 px-6 bg-gradient-to-r from-green-500 to-emerald-600 text-white font-semibold rounded-lg hover:from-green-600 hover:to-emerald-700 transition-all"
            >
              Go to Dashboard
            </Link>

            <Link
              href="/pricing"
              className="block w-full py-3 px-6 border border-slate-600 text-slate-300 font-semibold rounded-lg hover:bg-slate-700 transition-colors"
            >
              View Pricing
            </Link>
          </div>

          <p className="text-slate-500 text-xs mt-6">
            Questions? Contact{' '}
            <a href="mailto:support@smartertips.com" className="text-slate-300 hover:text-white">
              support@smartertips.com
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}

export default function CheckoutSuccessPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center">
        <p className="text-slate-400">Loading...</p>
      </div>
    }>
      <CheckoutSuccessContent />
    </Suspense>
  );
}
