'use client';

import { useAuth } from '@/app/lib/auth-context';
import { useState } from 'react';
import Link from 'next/link';

export default function Home() {
  const { user, loading: authLoading, signOut } = useAuth();
  const [isOpen, setIsOpen] = useState(false);

  const handleSignOut = () => {
    signOut();
    setIsOpen(false);
    setTimeout(() => {
      window.location.href = '/';
    }, 500);
  };

  const freeTools = [
    {
      id: 'defense-rankings',
      name: 'Defense Rankings',
      description: 'Analyze NBA team defensive performance by position and stat',
      icon: '📊',
      color: 'from-blue-500 to-blue-600',
      href: '/tools/defense-rankings',
      badge: 'FREE',
    },
    {
      id: 'teammate-impact',
      name: 'Teammate Impact',
      description: 'See how player stats change when a star player is absent',
      icon: '⚡',
      color: 'from-amber-500 to-orange-600',
      href: '/tools/teammate-impact',
      badge: 'FREE',
    },
  ];

  const premiumTools = [
    {
      id: 'line-comparison',
      name: 'Line Comparison',
      description: 'Compare betting lines across all major sportsbooks',
      icon: '📈',
      color: 'from-purple-500 to-pink-600',
      href: '/pricing',
      badge: 'PREMIUM',
    },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Navigation */}
      <nav className="border-b border-slate-700 bg-slate-900/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Logo */}
            <div className="flex items-center gap-2">
              <div className="text-2xl font-bold bg-gradient-to-r from-amber-400 to-orange-500 bg-clip-text text-transparent">
                SmarterTips
              </div>
            </div>

            {/* Right side - Auth buttons */}
            <div className="flex items-center gap-4">
              {!authLoading && !user ? (
                <>
                  <Link
                    href="/login"
                    className="text-slate-300 hover:text-white transition-colors"
                  >
                    Login
                  </Link>
                  <Link
                    href="/signup"
                    className="px-4 py-2 bg-gradient-to-r from-amber-500 to-orange-600 text-white rounded-lg hover:from-amber-600 hover:to-orange-700 transition-all"
                  >
                    Sign Up
                  </Link>
                </>
              ) : (
                <div className="relative">
                  <button
                    onClick={() => setIsOpen(!isOpen)}
                    className="flex items-center gap-2 px-4 py-2 text-slate-300 hover:text-white transition-colors"
                  >
                    <div className="w-8 h-8 bg-gradient-to-r from-amber-500 to-orange-600 rounded-full flex items-center justify-center text-white text-sm font-bold">
                      {user?.email?.[0]?.toUpperCase() || 'U'}
                    </div>
                    <span className="text-sm">{user?.email?.split('@')[0]}</span>
                  </button>

                  {isOpen && (
                    <div className="absolute right-0 mt-2 w-48 bg-slate-800 border border-slate-700 rounded-lg shadow-lg py-2 z-10">
                      <div className="px-4 py-2 border-b border-slate-700 text-sm text-slate-400">
                        {user?.email}
                      </div>
                      <Link
                        href="/pricing"
                        className="block px-4 py-2 text-slate-300 hover:text-white hover:bg-slate-700/50 transition-colors"
                      >
                        Premium
                      </Link>
                      <button
                        onClick={handleSignOut}
                        className="w-full text-left px-4 py-2 text-slate-300 hover:text-white hover:bg-slate-700/50 transition-colors"
                      >
                        Sign Out
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Hero Section */}
        <div className="text-center mb-16">
          <h1 className="text-4xl md:text-5xl font-bold text-white mb-4">
            NBA Betting Intelligence
          </h1>
          <p className="text-xl text-slate-400 max-w-2xl mx-auto">
            Professional-grade tools to analyze team defense, player impact, and betting opportunities
          </p>
        </div>

        {/* Free Tools Section */}
        <div className="mb-16">
          <div className="flex items-center gap-3 mb-8">
            <h2 className="text-2xl font-bold text-white">Free Tools</h2>
            <span className="text-xs bg-green-500/20 text-green-400 px-3 py-1 rounded-full">
              No login required
            </span>
          </div>
          <div className="grid md:grid-cols-2 gap-6">
            {freeTools.map((tool) => (
              <Link key={tool.id} href={tool.href}>
                <div className="h-full p-6 bg-slate-800/50 border border-slate-700 rounded-xl hover:border-slate-600 transition-all hover:bg-slate-800/70 cursor-pointer group">
                  <div className="flex justify-between items-start mb-3">
                    <span className="text-4xl">{tool.icon}</span>
                    <span className="text-xs font-bold bg-green-500/20 text-green-400 px-2 py-1 rounded">
                      {tool.badge}
                    </span>
                  </div>
                  <h3 className="text-xl font-bold text-white mb-2 group-hover:text-amber-400 transition-colors">
                    {tool.name}
                  </h3>
                  <p className="text-slate-400">{tool.description}</p>
                  <div className={`mt-4 h-1 bg-gradient-to-r ${tool.color} rounded-full`}></div>
                </div>
              </Link>
            ))}
          </div>
        </div>

        {/* Premium Tools Section */}
        <div className="mb-16">
          <div className="flex items-center gap-3 mb-8">
            <h2 className="text-2xl font-bold text-white">Premium Tools</h2>
            <span className="text-xs bg-purple-500/20 text-purple-400 px-3 py-1 rounded-full">
              Unlock with subscription
            </span>
          </div>
          <div className="grid md:grid-cols-2 gap-6">
            {premiumTools.map((tool) => (
              <Link key={tool.id} href={tool.href}>
                <div className="h-full p-6 bg-slate-800/50 border border-slate-700 rounded-xl hover:border-slate-600 transition-all hover:bg-slate-800/70 cursor-pointer group relative overflow-hidden">
                  <div className="absolute inset-0 bg-gradient-to-r from-purple-500/5 to-pink-500/5 opacity-0 group-hover:opacity-100 transition-opacity"></div>
                  <div className="relative z-10">
                    <div className="flex justify-between items-start mb-3">
                      <span className="text-4xl">{tool.icon}</span>
                      <span className="text-xs font-bold bg-purple-500/20 text-purple-400 px-2 py-1 rounded">
                        {tool.badge}
                      </span>
                    </div>
                    <h3 className="text-xl font-bold text-white mb-2 group-hover:text-purple-400 transition-colors">
                      {tool.name}
                    </h3>
                    <p className="text-slate-400">{tool.description}</p>
                    <div className={`mt-4 h-1 bg-gradient-to-r ${tool.color} rounded-full`}></div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>

        {/* CTA Section */}
        {!user && (
          <div className="bg-gradient-to-r from-amber-500/10 to-orange-600/10 border border-amber-500/20 rounded-xl p-8 text-center">
            <h3 className="text-2xl font-bold text-white mb-4">
              Ready to upgrade?
            </h3>
            <p className="text-slate-400 mb-6">
              Sign up to unlock premium tools and get detailed analysis
            </p>
            <div className="flex gap-4 justify-center">
              <Link
                href="/signup"
                className="px-6 py-3 bg-gradient-to-r from-amber-500 to-orange-600 text-white rounded-lg hover:from-amber-600 hover:to-orange-700 transition-all font-semibold"
              >
                Get Started
              </Link>
              <Link
                href="/pricing"
                className="px-6 py-3 border border-slate-600 text-white rounded-lg hover:bg-slate-800/50 transition-all font-semibold"
              >
                View Pricing
              </Link>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
