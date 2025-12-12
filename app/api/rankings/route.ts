import { createClient } from '@supabase/supabase-js'
import { NextRequest, NextResponse } from 'next/server'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { team, selected_stats = ['PTS', 'REB'], time_period = '2025-26' } = body

    if (!team) {
      return NextResponse.json({ error: 'Team name required' }, { status: 400 })
    }

    // Query Supabase
    const { data, error } = await supabase
      .from('nba_stats')
      .select('*')
      .eq('time_period', time_period)

    console.log('Query time_period:', time_period)
    console.log('Query error:', error)
    console.log('Data count:', data?.length)
    if (data && data.length > 0) {
      console.log('Sample row:', data[0])
    }

    if (error) throw error
    if (!data || data.length === 0) {
      return NextResponse.json({ 
        error: 'No data found',
        debug: { time_period, data_count: data?.length }
      }, { status: 404 })
    }

    // Pivot data (group by team+position, put stats in columns)
    const pivoted = new Map()
    for (const row of data) {
      const key = `${row.team}|${row.position}`
      if (!pivoted.has(key)) {
        pivoted.set(key, { team: row.team, position: row.position })
      }
      pivoted.get(key)[row.stat_name.toLowerCase()] = row.value
    }

    const team_data = Array.from(pivoted.values()).filter(
      (r: any) => r.team.toLowerCase() === team.toLowerCase()
    )

    if (team_data.length === 0) {
      return NextResponse.json({ error: 'Team not found' }, { status: 404 })
    }

    // Simple ranking calculation
    const results = []
    const POSITIONS = ['PG', 'SG', 'SF', 'PF', 'C']

    for (const position of POSITIONS) {
      const pos_teams = Array.from(pivoted.values()).filter((r: any) => r.position === position)
      const team_for_pos = team_data.find((r: any) => r.position === position)

      if (!team_for_pos) continue

      for (const stat of selected_stats) {
        const stat_lower = stat.toLowerCase()
        const team_val = team_for_pos[stat_lower]
        if (!team_val) continue

        const avg = pos_teams.reduce((sum: number, r: any) => sum + (r[stat_lower] || 0), 0) / pos_teams.length
        const pct_diff = ((team_val - avg) / avg) * 100
        const rank = pos_teams.filter((r: any) => r[stat_lower] < team_val).length + 1

        results.push({
          team: team,
          stat: stat,
          position,
          value: team_val,
          pct_diff: Math.round(pct_diff * 100) / 100,
          rank,
          total_teams: pos_teams.length,
        })
      }
    }

    return NextResponse.json({ team, time_period, results: results.slice(0, 20) })
  } catch (err: any) {
    console.error(err)
    return NextResponse.json({ error: err.message }, { status: 500 })
  }
}
