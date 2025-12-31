'use client';

import { useRouter } from 'next/navigation';
import { useAuth } from '@/app/lib/auth-context';
import { useEffect } from 'react';
import Link from 'next/link';

export default function ToolsDashboard() {
  const router = useRouter();
  const { user, loading: authLoading, signOut } = useAuth();

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login');
    }
  }, [user, authLoading, router]);

  const handleSignOut = () => {
    // Call signOut but don't wait for it
    signOut();
    // Redirect immediately
    setTimeout(() => {
      window.location.href = '/login';
    }, 500);
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

  const tools = [
    {
      id: 'defense-rankings',
      name: 'Defense Rankings',
      description: 'Analyze NBA team defensive performance by position and stat',
      icon: '📊',
      color: 'from-blue-500 to-blue-600',
      href: '/tools/defense-rankings',
    },
    {
      id: 'teammate-impact',
      name: 'Teammate Impact',
      description: 'Evaluate player impact and chemistry with teammates',
      icon: '👥',
      color: 'from-purple-500 to-purple-600',
      href: '/tools/teammate-impact',
      disabled: true,
    },
    {
      id: 'line-comparison',
      name: 'Line Comparison',
      description: 'Compare betting lines across sportsbooks and find value',
      icon: '📈',
      color: 'from-green-500 to-green-600',
      href: '/tools/line-comparison',
      disabled: true,
    },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-4 sm:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-12 flex justify-between items-start">
          <div>
            <h1 className="text-5xl font-bold text-white mb-2">NBA Tools</h1>
            <p className="text-slate-400 text-lg">Advanced betting analysis suite</p>
          </div>
          <div className="bg-slate-800 rounded-lg p-4 border border-slate-700 text-right">
            <p className="text-sm text-slate-400">Welcome back</p>
            <p className="text-white font-semibold">{user.email}</p>
            <div className="mt-3 flex gap-2">
              <Link
                href="/pricing"
                className="flex-1 px-3 py-2 bg-amber-600 hover:bg-amber-700 text-white text-sm rounded font-medium transition-colors duration-200"
              >
                Upgrade
              </Link>
              <button
                onClick={handleSignOut}
                type="button"
                className="flex-1 px-3 py-2 bg-red-600 hover:bg-red-700 text-white text-sm rounded font-medium transition-colors duration-200"
              >
                Sign Out
              </button>
            </div>
          </div>
        </div>

        {/* Tools Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {tools.map((tool) => (
            <div key={tool.id} className="group relative">
              {tool.disabled && (
                <div className="absolute inset-0 bg-black/40 rounded-lg flex items-center justify-center z-20 backdrop-blur-sm">
                  <span className="text-white font-semibold">Coming Soon</span>
                </div>
              )}
              
              <Link href={tool.disabled ? '#' : tool.href}>
                <div
                  className={`h-full bg-gradient-to-br ${tool.color} rounded-lg p-6 shadow-xl border border-slate-700 transform transition-all duration-200 ${
                    !tool.disabled
                      ? 'hover:scale-105 hover:shadow-2xl cursor-pointer'
                      : 'opacity-60 cursor-not-allowed'
                  }`}
                >
                  {/* Icon */}
                  <div className="text-6xl mb-4">{tool.icon}</div>

                  {/* Content */}
                  <h2 className="text-2xl font-bold text-white mb-2">{tool.name}</h2>
                  <p className="text-white/80 text-sm mb-6 leading-relaxed">
                    {tool.description}
                  </p>

                  {/* Button */}
                  {!tool.disabled && (
                    <div className="flex items-center text-white font-semibold">
                      Access Tool
                      <svg
                        className="w-5 h-5 ml-2 transform group-hover:translate-x-1 transition-transform"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M9 5l7 7-7 7"
                        />
                      </svg>
                    </div>
                  )}
                </div>
              </Link>
            </div>
          ))}
        </div>

        {/* Coming Soon Section */}
        <div className="mt-12 text-center">
          <h3 className="text-xl font-semibold text-slate-300 mb-2">
            More tools coming soon
          </h3>
          <p className="text-slate-400">
            We are constantly adding new features to help you make better betting decisions
          </p>
        </div>
      </div>
    </div>
  );
}
