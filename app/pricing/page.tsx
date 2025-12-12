'use client';

import { useRouter } from 'next/navigation';
import { useAuth } from '@/app/lib/auth-context';
import { useEffect, useState } from 'react';
import Link from 'next/link';

export default function PricingPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const [isLoading, setIsLoading] = useState(false);

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login');
    }
  }, [user, authLoading, router]);

  const handleUpgradeClick = async () => {
    if (!user) return;
    
    setIsLoading(true);
    try {
      // Call checkout API route
      const response = await fetch('/api/checkout', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          userId: user.id,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to create checkout session');
      }

      const { url } = await response.json();
      
      // Redirect to Stripe checkout
      if (url) {
        window.location.href = url;
      }
    } catch (error) {
      console.error('Checkout error:', error);
      alert('Failed to start checkout. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

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
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Header with back button */}
      <div className="border-b border-slate-700 bg-slate-900/50 backdrop-blur">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
          <Link
            href="/app"
            className="flex items-center gap-2 text-slate-400 hover:text-slate-200 transition-colors"
          >
            <span>←</span>
            <span>Back to Dashboard</span>
          </Link>
        </div>
      </div>

      {/* Main content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        {/* Title section */}
        <div className="text-center mb-16">
          <h1 className="text-4xl md:text-5xl font-bold text-white mb-4">
            Choose Your Plan
          </h1>
          <p className="text-lg text-slate-400">
            Unlock premium NBA analytics tools and insights
          </p>
        </div>

        {/* Pricing cards grid */}
        <div className="grid md:grid-cols-2 gap-8 max-w-5xl mx-auto">
          {/* Free tier */}
          <div className="relative bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 rounded-lg p-8 flex flex-col">
            <div className="mb-6">
              <h2 className="text-2xl font-bold text-white mb-2">Free</h2>
              <p className="text-slate-400">Start with the basics</p>
            </div>

            <div className="mb-8">
              <div className="flex items-baseline gap-2">
                <span className="text-4xl font-bold text-white">$0</span>
                <span className="text-slate-400">/month</span>
              </div>
            </div>

            <ul className="space-y-4 mb-8 flex-1">
              <li className="flex items-start gap-3">
                <span className="text-green-400 font-bold mt-0.5">✓</span>
                <span className="text-slate-300">Defense Rankings tool</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-green-400 font-bold mt-0.5">✓</span>
                <span className="text-slate-300">Basic NBA team analytics</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-green-400 font-bold mt-0.5">✓</span>
                <span className="text-slate-300">Community support</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-slate-600 font-bold mt-0.5">✗</span>
                <span className="text-slate-500">Advanced tools (coming soon)</span>
              </li>
            </ul>

            <button
              disabled
              className="w-full py-3 px-6 rounded-lg bg-slate-700 text-slate-400 font-semibold cursor-not-allowed"
            >
              Current Plan
            </button>
          </div>

          {/* Premium tier */}
          <div className="relative bg-gradient-to-br from-amber-500/20 via-orange-500/10 to-slate-900 border border-amber-500/50 rounded-lg p-8 flex flex-col ring-2 ring-amber-500/30">
            <div className="absolute top-0 right-0 bg-amber-500 text-slate-900 px-4 py-1 rounded-bl-lg font-bold text-sm">
              POPULAR
            </div>

            <div className="mb-6 mt-4">
              <h2 className="text-2xl font-bold text-white mb-2">Premium</h2>
              <p className="text-slate-400">Advanced analytics & tools</p>
            </div>

            <div className="mb-8">
              <div className="flex items-baseline gap-2">
                <span className="text-4xl font-bold text-white">$9.99</span>
                <span className="text-slate-400">/month</span>
              </div>
              <p className="text-sm text-slate-500 mt-2">Cancel anytime</p>
            </div>

            <ul className="space-y-4 mb-8 flex-1">
              <li className="flex items-start gap-3">
                <span className="text-green-400 font-bold mt-0.5">✓</span>
                <span className="text-slate-300">All Free plan features</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-green-400 font-bold mt-0.5">✓</span>
                <span className="text-slate-300">Teammate Impact tool</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-green-400 font-bold mt-0.5">✓</span>
                <span className="text-slate-300">Line Comparison tool</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-green-400 font-bold mt-0.5">✓</span>
                <span className="text-slate-300">Advanced player analytics</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-green-400 font-bold mt-0.5">✓</span>
                <span className="text-slate-300">Priority support</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-green-400 font-bold mt-0.5">✓</span>
                <span className="text-slate-300">Early access to new tools</span>
              </li>
            </ul>

            <button
              onClick={handleUpgradeClick}
              disabled={isLoading}
              className="w-full py-3 px-6 rounded-lg bg-gradient-to-r from-amber-500 to-orange-500 text-white font-semibold hover:from-amber-600 hover:to-orange-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? 'Processing...' : 'Upgrade to Premium'}
            </button>
          </div>
        </div>

        {/* FAQ section */}
        <div className="max-w-3xl mx-auto mt-20">
          <h2 className="text-2xl font-bold text-white mb-8 text-center">
            Common Questions
          </h2>

          <div className="space-y-6">
            <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-6">
              <h3 className="text-lg font-semibold text-white mb-2">
                Can I cancel anytime?
              </h3>
              <p className="text-slate-400">
                Yes, you can cancel your subscription at any time. Your access will continue until the end of your billing cycle.
              </p>
            </div>

            <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-6">
              <h3 className="text-lg font-semibold text-white mb-2">
                What payment methods do you accept?
              </h3>
              <p className="text-slate-400">
                We accept all major credit and debit cards through Stripe. Your payment information is securely processed.
              </p>
            </div>

            <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-6">
              <h3 className="text-lg font-semibold text-white mb-2">
                Do you offer refunds?
              </h3>
              <p className="text-slate-400">
                We're confident you'll love SmarterTips. If you have issues within the first 7 days, contact support for assistance.
              </p>
            </div>

            <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-6">
              <h3 className="text-lg font-semibold text-white mb-2">
                When will the other tools be available?
              </h3>
              <p className="text-slate-400">
                Teammate Impact and Line Comparison tools are coming soon. Premium subscribers will get early access!
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
