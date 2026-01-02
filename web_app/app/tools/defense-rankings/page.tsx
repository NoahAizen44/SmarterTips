'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useAuth } from '@/app/lib/auth-context';

const NBA_TEAMS = [
  'Atlanta', 'Boston', 'Brooklyn', 'Charlotte', 'Chicago', 'Cleveland', 'Dallas', 'Denver',
  'Detroit', 'Golden State', 'Houston', 'LA Clippers', 'LA Lakers', 'Memphis', 'Miami',
  'Milwaukee', 'Minnesota', 'New Orleans', 'New York', 'Oklahoma City', 'Orlando', 'Philadelphia',
  'Phoenix', 'Portland', 'Sacramento', 'San Antonio', 'Toronto', 'Utah', 'Washington'
];

const STATS = ['PTS', 'REB', 'AST', '3PM', 'STL', 'BLK'];
const TIME_PERIODS = ['2025-26', 'Last 15', 'Last 7'];

interface RankingResult {
  team: string;
  stat: string;
  position: string;
  value: number;
  pct_diff: number;
  rank: number;
  total_teams: number;
}

interface RankingResponse {
  team: string;
  time_period: string;
  results: RankingResult[];
}

export default function DefenseRankings() {
  const { user, profile, loading: authLoading, signOut } = useAuth();
  const [selectedTeams, setSelectedTeams] = useState<string[]>(['Atlanta']);
  const [selectedStats, setSelectedStats] = useState<string[]>(['PTS']);
  const [selectedPeriod, setSelectedPeriod] = useState<string>('2025-26');
  const [sortColumn, setSortColumn] = useState<keyof RankingResult>('rank');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<RankingResult[] | null>(null);

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

  const toggleTeam = (team: string) => {
    setSelectedTeams(prev => 
      prev.includes(team) 
        ? prev.filter(t => t !== team)
        : [...prev, team]
    );
  };

  const toggleStat = (stat: string) => {
    setSelectedStats(prev => 
      prev.includes(stat) 
        ? prev.filter(s => s !== stat)
        : [...prev, stat]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResults(null);

    if (selectedTeams.length === 0) {
      setError('Please select at least one team');
      setLoading(false);
      return;
    }

    try {
      const allResults: RankingResult[] = [];

      for (const team of selectedTeams) {
        const response = await fetch('/api/rankings', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            team: team,
            selected_stats: selectedStats.length > 0 ? selectedStats : STATS,
            time_period: selectedPeriod,
          }),
        });

        if (!response.ok) {
          throw new Error(`Failed to fetch rankings for ${team}`);
        }

        const data: RankingResponse = await response.json();
        allResults.push(...data.results);
      }

      // Don't sort here - user will click headers to sort
      setResults(allResults);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleSort = (col: keyof RankingResult) => {
    if (sortColumn === col) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(col);
      setSortDir('asc');
    }
  };

  const getSorted = () => {
    if (!results) return [];
    return [...results].sort((a, b) => {
      const aVal = a[sortColumn];
      const bVal = b[sortColumn];
      
      let cmp = 0;
      if (typeof aVal === 'string' && typeof bVal === 'string') {
        cmp = aVal.localeCompare(bVal);
      } else if (typeof aVal === 'number' && typeof bVal === 'number') {
        cmp = aVal - bVal;
      }
      
      return sortDir === 'asc' ? cmp : -cmp;
    });
  };

  const getPositionColor = (pct_diff: number): string => {
    if (pct_diff > 5) return 'text-green-400 font-semibold';
    if (pct_diff > 0) return 'text-green-300';
    if (pct_diff > -5) return 'text-red-300';
    return 'text-red-400 font-semibold';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-4 sm:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header with User Info */}
        <div className="mb-8 flex justify-between items-start">
          <div>
            <Link href="/" className="text-slate-400 hover:text-slate-300 text-sm mb-2 inline-block">
              ← Back to Tools
            </Link>
            <h1 className="text-4xl sm:text-5xl font-bold text-white mb-2">
              NBA Defense Rankings
            </h1>
            <p className="text-slate-400 text-lg">
              Analyze team defensive performance by position and stat
            </p>
          </div>
          <div className="bg-slate-800 rounded-lg p-4 border border-slate-700 text-right">
            <p className="text-sm text-slate-400">Logged in as</p>
            <p className="text-white font-semibold">{profile?.full_name || user?.email}</p>
            <p className="text-xs text-blue-400 mt-1 capitalize">{profile?.subscription_tier || 'free'} Plan</p>
            <button
              onClick={handleSignOut}
              type="button"
              className="mt-3 w-full px-3 py-2 bg-red-600 hover:bg-red-700 text-white text-sm rounded font-medium transition-colors duration-200"
            >
              Sign Out
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Controls Panel */}
          <div className="lg:col-span-1">
            <form onSubmit={handleSubmit} className="bg-slate-800 rounded-lg p-6 shadow-xl border border-slate-700">

              {/* Team Selection */}
              <div className="mb-6">
                <label className="block text-sm font-semibold text-slate-100 mb-3">
                  Teams
                </label>
                <div className="grid grid-cols-2 gap-2 max-h-56 overflow-y-auto">
                  {NBA_TEAMS.map(team => (
                    <label key={team} className="flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={selectedTeams.includes(team)}
                        onChange={() => toggleTeam(team)}
                        className="w-4 h-4 text-blue-500 bg-slate-700 border-slate-600 rounded focus:ring-2 focus:ring-blue-500"
                      />
                      <span className="ml-2 text-slate-300 text-sm">{team}</span>
                    </label>
                  ))}
                </div>
              </div>

              {/* Time Period */}
              <div className="mb-6">
                <label className="block text-sm font-semibold text-slate-100 mb-3">
                  Time Period
                </label>
                <div className="space-y-2">
                  {TIME_PERIODS.map(period => (
                    <label key={period} className="flex items-center cursor-pointer">
                      <input
                        type="radio"
                        name="period"
                        value={period}
                        checked={selectedPeriod === period}
                        onChange={(e) => setSelectedPeriod(e.target.value)}
                        className="w-4 h-4 text-blue-500 bg-slate-700 border-slate-600 focus:ring-2 focus:ring-blue-500"
                      />
                      <span className="ml-3 text-slate-300">{period}</span>
                    </label>
                  ))}
                </div>
              </div>

              {/* Stats Selection */}
              <div className="mb-6">
                <label className="block text-sm font-semibold text-slate-100 mb-3">
                  Stats to Display
                </label>
                <div className="space-y-2">
                  {STATS.map(stat => (
                    <label key={stat} className="flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={selectedStats.includes(stat)}
                        onChange={() => toggleStat(stat)}
                        className="w-4 h-4 text-blue-500 bg-slate-700 border-slate-600 rounded focus:ring-2 focus:ring-blue-500"
                      />
                      <span className="ml-3 text-slate-300">{stat}</span>
                    </label>
                  ))}
                </div>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold py-3 rounded-md transition-all duration-200"
              >
                {loading ? 'Loading...' : 'Get Rankings'}
              </button>
            </form>
          </div>

          {/* Results Panel */}
          <div className="lg:col-span-3">
            {error && (
              <div className="bg-red-900 border border-red-700 text-red-100 px-6 py-4 rounded-lg mb-6">
                <p className="font-semibold">Error</p>
                <p className="text-sm">{error}</p>
              </div>
            )}

            {results && results.length > 0 ? (
              <div className="bg-slate-800 rounded-lg overflow-hidden shadow-xl border border-slate-700">
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-slate-700 border-b border-slate-600">
                      <tr>
                        <th onClick={() => handleSort('team')} className="px-6 py-4 text-left text-sm font-semibold text-slate-300 cursor-pointer hover:text-blue-400">Team {sortColumn === 'team' && (sortDir === 'asc' ? '▲' : '▼')}</th>
                        <th onClick={() => handleSort('stat')} className="px-6 py-4 text-left text-sm font-semibold text-slate-300 cursor-pointer hover:text-blue-400">Stat {sortColumn === 'stat' && (sortDir === 'asc' ? '▲' : '▼')}</th>
                        <th onClick={() => handleSort('position')} className="px-6 py-4 text-left text-sm font-semibold text-slate-300 cursor-pointer hover:text-blue-400">Position {sortColumn === 'position' && (sortDir === 'asc' ? '▲' : '▼')}</th>
                        <th onClick={() => handleSort('value')} className="px-6 py-4 text-right text-sm font-semibold text-slate-300 cursor-pointer hover:text-blue-400">Value {sortColumn === 'value' && (sortDir === 'asc' ? '▲' : '▼')}</th>
                        <th onClick={() => handleSort('pct_diff')} className="px-6 py-4 text-right text-sm font-semibold text-slate-300 cursor-pointer hover:text-blue-400">vs Avg {sortColumn === 'pct_diff' && (sortDir === 'asc' ? '▲' : '▼')}</th>
                        <th onClick={() => handleSort('rank')} className="px-6 py-4 text-right text-sm font-semibold text-slate-300 cursor-pointer hover:text-blue-400">Rank {sortColumn === 'rank' && (sortDir === 'asc' ? '▲' : '▼')}</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-700">
                      {getSorted().map((result, idx) => (
                        <tr key={idx} className="hover:bg-slate-700 transition-colors">
                          <td className="px-6 py-4 text-sm font-semibold text-blue-400">{result.team}</td>
                          <td className="px-6 py-4 text-sm font-semibold text-white">{result.stat}</td>
                          <td className="px-6 py-4 text-sm text-slate-300">{result.position}</td>
                          <td className="px-6 py-4 text-sm text-right text-slate-300">{result.value.toFixed(2)}</td>
                          <td className={`px-6 py-4 text-sm text-right font-medium ${getPositionColor(result.pct_diff)}`}>
                            {result.pct_diff > 0 ? '+' : ''}{result.pct_diff.toFixed(2)}%
                          </td>
                          <td className="px-6 py-4 text-sm text-right text-slate-300">
                            {result.rank}/{result.total_teams}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : (
              <div className="bg-slate-800 rounded-lg p-12 text-center border border-slate-700">
                <p className="text-slate-400">
                  {loading ? 'Fetching rankings...' : 'Select a team and click "Get Rankings" to see results'}
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
