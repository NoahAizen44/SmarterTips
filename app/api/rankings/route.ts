import { createClient } from '@supabase/supabase-js'
import { NextRequest, NextResponse } from 'next/server'
import { requireAuth, badRequest, serverError } from '@/lib/apiAuth'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)

// Valid stats list
const VALID_STATS = ['PTS', 'REB', 'AST', 'FG%', 'FT%', 'TOV', '3PM', '3PA']

// Validation helpers
function isValidTeam(team: unknown): team is string {
  if (typeof team !== 'string') return false
  if (team.length < 2 || team.length > 50) return false
  // Allow letters, spaces, apostrophes, hyphens
  return /^[a-zA-Z\s\-']+$/.test(team)
}

function isValidStats(stats: unknown): stats is string[] {
  if (!Array.isArray(stats)) return false
  if (stats.length === 0 || stats.length > 5) return false
  
  return stats.every(s => 
    typeof s === 'string' && 
    VALID_STATS.includes(s.toUpperCase()) &&
    s.length > 0 &&
    s.length <= 10
  )
}

function isValidTimePeriod(period: unknown): period is string {
  if (typeof period !== 'string') return false
  // Allow formats like "2025-26", "2024-25"
  return /^\d{4}-\d{2}$/.test(period)
}

export async function POST(request: NextRequest) {
  try {
    // 1. Verify the user is authenticated
    await requireAuth(request)

    // 2. Parse request body
    let body: unknown
    try {
      body = await request.json()
    } catch {
      return badRequest('Invalid JSON in request body')
    }

    // 3. Extract and validate inputs
    const rawTeam = (body as Record<string, unknown>)?.team
    const rawStats = (body as Record<string, unknown>)?.selected_stats
    const rawTimePeriod = (body as Record<string, unknown>)?.time_period

    if (!isValidTeam(rawTeam)) {
      return badRequest('Invalid team name')
    }

    if (!isValidStats(rawStats)) {
      return badRequest('Invalid stats selection')
    }

    const timePeriod = isValidTimePeriod(rawTimePeriod) ? rawTimePeriod : '2025-26'

    // 4. Query Supabase with validated inputs
    const { data, error } = await supabase
      .from('nba_stats')
      .select('*')
      .eq('time_period', timePeriod)

    if (error) {
      console.error('Query error:', error)
      return serverError()
    }

    if (!data || data.length === 0) {
      return badRequest('No data found for the requested time period')
    }

    // 5. Pivot data (group by team+position, put stats in columns)
    const pivoted = new Map()
    for (const row of data as Array<Record<string, unknown>>) {
      const team = row.team as string
      const position = row.position as string
      const key = `${team}|${position}`
      
      if (!pivoted.has(key)) {
        pivoted.set(key, { team, position })
      }
      
      const statName = (row.stat_name as string)?.toLowerCase() || ''
      const value = row.value as number
      pivoted.get(key)[statName] = value
    }

    // 6. Filter for requested team
    const teamData = Array.from(pivoted.values()).filter(
      (r: Record<string, unknown>) => (r.team as string).toLowerCase() === rawTeam.toLowerCase()
    )

    if (teamData.length === 0) {
      return badRequest('Team not found')
    }

    // 7. Calculate rankings
    const results: Array<Record<string, unknown>> = []
    const POSITIONS = ['PG', 'SG', 'SF', 'PF', 'C']

    for (const position of POSITIONS) {
      const posTeams = Array.from(pivoted.values()).filter(
        (r: Record<string, unknown>) => r.position === position
      )

      const teamForPos = teamData.find((r: Record<string, unknown>) => r.position === position)

      if (!teamForPos) continue

      for (const stat of rawStats) {
        const statLower = stat.toLowerCase()
        const teamVal = teamForPos[statLower] as number | undefined
        
        if (!teamVal) continue

        const avgSum = posTeams.reduce((sum: number, r: Record<string, unknown>) => {
          const val = (r[statLower] as number) || 0
          return sum + val
        }, 0)
        
        const avg = avgSum / posTeams.length
        const pctDiff = ((teamVal - avg) / avg) * 100
        const rank = posTeams.filter(
          (r: Record<string, unknown>) => ((r[statLower] as number) || 0) < teamVal
        ).length + 1

        results.push({
          team: rawTeam,
          stat,
          position,
          value: teamVal,
          pct_diff: Math.round(pctDiff * 100) / 100,
          rank,
          total_teams: posTeams.length,
        })
      }
    }

    return NextResponse.json({
      team: rawTeam,
      time_period: timePeriod,
      results: results.slice(0, 20),
    })
  } catch (err) {
    if (err instanceof Error && err.message === 'UNAUTHORIZED') {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      )
    }

    console.error('Server error:', err)
    return serverError()
  }
}
