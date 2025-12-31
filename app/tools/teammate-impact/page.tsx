'use client'

import React, { useState, useEffect, Suspense } from 'react'
import { useAuth } from '@/app/lib/auth-context'

const STATS_LIST = ['PTS', 'REB', 'AST', '3PM', '3PA', 'STL', 'BLK']

interface PlayerImpact {
  player: string
  with_star: number
  without_star: number
  impact_pct: number
  rank: number
  games_with_star: number
  games_without_star: number
}

function TeammateImpactContent() {
  const { loading: authLoading } = useAuth()
  const [selectedTeam, setSelectedTeam] = useState('')
  const [teamsDropdownOpen, setTeamsDropdownOpen] = useState(false)
  const [selectedStat, setSelectedStat] = useState('PTS')
  const [statDropdownOpen, setStatDropdownOpen] = useState(false)
  const [selectedAbsentPlayer, setSelectedAbsentPlayer] = useState('')
  const [playersDropdownOpen, setPlayersDropdownOpen] = useState(false)
  const [teams, setTeams] = useState<string[]>([])
  const [teamPlayers, setTeamPlayers] = useState<string[]>([])
  const [sortBy, setSortBy] = useState<'ascending' | 'descending'>('descending')
  const [rankings, setRankings] = useState<PlayerImpact[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // Fetch teams on mount
  useEffect(() => {
    const fetchTeams = async () => {
      try {
        const res = await fetch('/api/teammate-impact?action=teams')
        const data = await res.json()
        console.log('Teams response:', data)
        if (data.success && data.teams && data.teams.length > 0) {
          setTeams(data.teams)
        } else {
          console.error('Teams API error:', data.error)
        }
      } catch (err) {
        console.error('Failed to load teams:', err)
      }
    }
    fetchTeams()
  }, [])

  // Fetch players when team changes
  useEffect(() => {
    if (!selectedTeam) {
      setTeamPlayers([])
      return
    }

    const fetchPlayers = async () => {
      try {
        const res = await fetch(
          `/api/teammate-impact?action=players&team=${encodeURIComponent(selectedTeam)}`
        )
        const data = await res.json()
        if (data.success) {
          setTeamPlayers(data.players)
        }
      } catch (err) {
        console.error('Failed to load players:', err)
      }
    }

    fetchPlayers()
  }, [selectedTeam])

  const handleTeamSelect = (team: string) => {
    setSelectedTeam(team)
    setTeamsDropdownOpen(false)
    setSelectedAbsentPlayer('')
    setRankings([])
  }

  const handlePlayerSelect = (player: string) => {
    setSelectedAbsentPlayer(player)
    setPlayersDropdownOpen(false)
    setRankings([])
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!selectedTeam) {
      setError('Please select a team')
      return
    }

    if (!selectedAbsentPlayer) {
      setError('Please select a player to analyze')
      return
    }

    setLoading(true)
    setError('')
    setRankings([])

    try {
      const res = await fetch('/api/teammate-impact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          team: selectedTeam,
          absent_player: selectedAbsentPlayer,
          stat: selectedStat,
        }),
      })

      const data = await res.json()

      if (res.ok && data.success) {
        const results = data.rankings

        // Sort results
        if (sortBy === 'ascending') {
          results.sort((a: PlayerImpact, b: PlayerImpact) => a.impact_pct - b.impact_pct)
        } else {
          results.sort((a: PlayerImpact, b: PlayerImpact) => b.impact_pct - a.impact_pct)
        }

        setRankings(results)
      } else {
        setError(data.error || 'Failed to analyze impact')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Connection error')
    } finally {
      setLoading(false)
    }
  }

  if (authLoading) {
    return <div className="flex justify-center items-center min-h-screen">Loading...</div>
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Header */}
      <div className="bg-slate-800/50 backdrop-blur border-b border-slate-700">
        <div className="max-w-7xl mx-auto px-6 py-8">
          <h1 className="text-4xl font-bold text-white mb-2">🏀 Teammate Impact</h1>
          <p className="text-slate-400">
            How much do player stats improve when the star player sits out?
          </p>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Sidebar */}
          <div className="lg:col-span-1 relative z-50">
            <form
              onSubmit={handleSubmit}
              className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-lg p-6 space-y-6"
            >
              {/* Team Selection */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-3">
                  Select Team
                </label>
                <div className="relative">
                  <button
                    type="button"
                    onClick={() => setTeamsDropdownOpen(!teamsDropdownOpen)}
                    className="w-full px-4 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-white text-left hover:bg-slate-700 transition-colors"
                  >
                    {selectedTeam || 'Select team'}
                  </button>
                  {teamsDropdownOpen && (
                    <div className="absolute top-full left-0 right-0 mt-1 bg-slate-700 border border-slate-600 rounded-lg shadow-lg z-50 max-h-60 overflow-y-auto">
                      {teams.map((team) => (
                        <button
                          key={team}
                          type="button"
                          onClick={() => handleTeamSelect(team)}
                          className="w-full px-4 py-2 text-left text-white hover:bg-slate-600 first:rounded-t-lg last:rounded-b-lg"
                        >
                          {team}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Player Selection */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-3">
                  Analyze Player (Absent)
                </label>
                <div className="relative">
                  <button
                    type="button"
                    onClick={() => setPlayersDropdownOpen(!playersDropdownOpen)}
                    disabled={!selectedTeam || teamPlayers.length === 0}
                    className="w-full px-4 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-white text-left hover:bg-slate-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {selectedAbsentPlayer || 'Select player'}
                  </button>
                  {playersDropdownOpen && teamPlayers.length > 0 && (
                    <div className="absolute top-full left-0 right-0 mt-1 bg-slate-700 border border-slate-600 rounded-lg shadow-lg z-50 max-h-60 overflow-y-auto">
                      {teamPlayers.map((player) => (
                        <button
                          key={player}
                          type="button"
                          onClick={() => handlePlayerSelect(player)}
                          className="w-full px-4 py-2 text-left text-white hover:bg-slate-600 first:rounded-t-lg last:rounded-b-lg"
                        >
                          {player}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Stat Selection */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-3">
                  Stat to Analyze
                </label>
                <div className="relative">
                  <button
                    type="button"
                    onClick={() => setStatDropdownOpen(!statDropdownOpen)}
                    className="w-full px-4 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-white text-left hover:bg-slate-700 transition-colors"
                  >
                    {selectedStat}
                  </button>
                  {statDropdownOpen && (
                    <div className="absolute top-full left-0 right-0 mt-1 bg-slate-700 border border-slate-600 rounded-lg shadow-lg z-10 max-h-60 overflow-y-auto">
                      {STATS_LIST.map((stat) => (
                        <button
                          key={stat}
                          type="button"
                          onClick={() => {
                            setSelectedStat(stat)
                            setStatDropdownOpen(false)
                          }}
                          className="w-full px-4 py-2 text-left text-white hover:bg-slate-600 first:rounded-t-lg last:rounded-b-lg"
                        >
                          {stat}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Sort By */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-3">
                  Sort By
                </label>
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as 'ascending' | 'descending')}
                  className="w-full px-4 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-white hover:bg-slate-700 transition-colors"
                >
                  <option value="descending">Impact % (Highest First)</option>
                  <option value="ascending">Impact % (Lowest First)</option>
                </select>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={loading}
                className="w-full py-2 bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 disabled:opacity-50 text-white font-semibold rounded-lg transition-all"
              >
                {loading ? 'Analyzing...' : 'Analyze Impact'}
              </button>

              {error && (
                <div className="bg-red-900/20 border border-red-700 rounded-lg p-3 text-red-200 text-sm">
                  {error}
                </div>
              )}
            </form>
          </div>

          {/* Results */}
          <div className="lg:col-span-3">
            {rankings.length > 0 ? (
              <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-lg p-6">
                <h2 className="text-2xl font-bold text-white mb-4">
                  {selectedAbsentPlayer} Impact on {selectedTeam} ({selectedStat})
                </h2>

                <div className="space-y-3">
                  {rankings.map((item) => (
                    <div
                      key={item.player}
                      className="bg-slate-700/30 border border-slate-600 rounded-lg p-4 hover:bg-slate-700/50 transition-colors"
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center gap-3">
                          <div className="flex items-center justify-center w-8 h-8 bg-amber-500/20 border border-amber-500 rounded-full text-amber-300 font-semibold text-sm">
                            {item.rank}
                          </div>
                          <div>
                            <h3 className="text-lg font-semibold text-white">{item.player}</h3>
                            <p className="text-slate-400 text-sm">
                              With: {item.with_star.toFixed(2)} ({item.games_with_star}G) | Without:{' '}
                              {item.without_star.toFixed(2)} ({item.games_without_star}G)
                            </p>
                          </div>
                        </div>
                        <div
                          className={`text-2xl font-bold ${
                            item.impact_pct > 0 ? 'text-green-400' : 'text-red-400'
                          }`}
                        >
                          {item.impact_pct > 0 ? '+' : ''}
                          {item.impact_pct.toFixed(1)}%
                        </div>
                      </div>

                      {/* Visual bar */}
                      <div className="flex items-center gap-2 h-6">
                        <div className="flex-1 bg-slate-600/50 rounded-full h-2 overflow-hidden">
                          <div
                            className={`h-full transition-all ${
                              item.impact_pct > 0 ? 'bg-green-500' : 'bg-red-500'
                            }`}
                            style={{
                              width: `${Math.min(Math.abs(item.impact_pct) / 2, 100)}%`,
                            }}
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-lg p-12 text-center">
                <p className="text-slate-400 text-lg">
                  Select a team and player to analyze their impact on teammates
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default function TeammateImpactPage() {
  return (
    <Suspense fallback={<div className="flex justify-center items-center min-h-screen">Loading...</div>}>
      <TeammateImpactContent />
    </Suspense>
  )
}
