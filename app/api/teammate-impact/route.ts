import { createClient } from '@supabase/supabase-js'
import { NextRequest, NextResponse } from 'next/server'
import { PLAYERS_BY_TEAM } from '@/lib/playersData'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)

interface GameLog {
  id: string
  team: string
  player_id: number
  player_name: string
  position: string
  game_date: string
  game_id: number
  pts: number
  reb: number
  ast: number
  '3pm': number
  '3pa': number
  stl: number
  blk: number
  season: number
}

interface PlayerImpact {
  player: string
  with_star: number
  without_star: number
  impact_pct: number
  rank: number
  games_with_star: number
  games_without_star: number
}

// Validation helpers
const VALID_STATS = ['PTS', 'REB', 'AST', '3PM', '3PA', 'STL', 'BLK']
const ALL_TEAMS = Object.keys(PLAYERS_BY_TEAM)

function validateTeam(team: unknown): string | null {
  if (typeof team !== 'string') return null
  if (!ALL_TEAMS.includes(team)) return null
  return team
}

function validatePlayer(player: unknown): string | null {
  if (typeof player !== 'string') return null
  if (player.length < 1 || player.length > 100) return null
  // Basic sanitization - allow letters, spaces, apostrophes, hyphens, dots
  if (!/^[a-zA-Z\s\-'.]*$/.test(player)) return null
  return player
}

function validateStat(stat: unknown): string {
  if (typeof stat !== 'string') return 'PTS'
  if (!VALID_STATS.includes(stat.toUpperCase())) return 'PTS'
  return stat.toUpperCase()
}

export async function POST(request: NextRequest) {
  try {
    // Parse JSON with error handling
    let body: unknown
    try {
      body = await request.json()
    } catch {
      return NextResponse.json(
        { error: 'Invalid JSON in request body' },
        { status: 400 }
      )
    }

    // Validate inputs
    const rawTeam = (body as Record<string, unknown>)?.team
    const rawPlayer = (body as Record<string, unknown>)?.absent_player
    const rawStat = (body as Record<string, unknown>)?.stat

    const team = validateTeam(rawTeam)
    if (!team) {
      return NextResponse.json(
        { error: 'Invalid or missing team parameter' },
        { status: 400 }
      )
    }

    const absent_player = validatePlayer(rawPlayer)
    if (!absent_player) {
      return NextResponse.json(
        { error: 'Invalid or missing absent_player parameter' },
        { status: 400 }
      )
    }

    const stat = validateStat(rawStat)

    // Fetch game data for the team
    const { data: gameData, error } = await supabase
      .from('player_game_logs')
      .select('*')
      .eq('team', team)

    if (error) {
      console.error('Database error:', error)
      return NextResponse.json(
        { error: 'Failed to fetch game data' },
        { status: 500 }
      )
    }

    if (!gameData || gameData.length === 0) {
      return NextResponse.json(
        { error: `No game data found for team ${team}` },
        { status: 404 }
      )
    }

    // Get all unique players on team
    const playerSet = new Set(gameData.map((g: GameLog) => g.player_name))
    const teamPlayers = Array.from(playerSet)

    // Find the absent player
    const absentPlayerData = gameData.filter(
      (g: GameLog) => g.player_name === absent_player
    )

    if (absentPlayerData.length === 0) {
      return NextResponse.json(
        { error: `Player ${absent_player} has no game data for ${team}. They may be injured or on the roster but haven't played yet.` },
        { status: 404 }
      )
    }

    // Get games where absent player played vs didn't play
    const gamesWithAbsentPlayer = new Set(
      absentPlayerData.map((g: GameLog) => g.game_id)
    )

    // Calculate stats for each teammate
    const impactResults: PlayerImpact[] = []
    const statKey = stat.toLowerCase() as string

    for (const playerName of teamPlayers) {
      if (playerName === absent_player) continue

      const playerGames = gameData.filter((g: GameLog) => g.player_name === playerName)

      if (playerGames.length === 0) continue

      // Split games: with and without absent player
      const gamesWithoutAbsentPlayer = playerGames.filter(
        (g: GameLog) => !gamesWithAbsentPlayer.has(g.game_id)
      )
      const gamesWithAbsentPlayerPresent = playerGames.filter(
        (g: GameLog) => gamesWithAbsentPlayer.has(g.game_id)
      )

      // Calculate average stat when absent player is playing
      const withStarAvg =
        gamesWithAbsentPlayerPresent.length > 0
          ? gamesWithAbsentPlayerPresent.reduce((sum, g: GameLog) => {
              const val = (g[statKey as keyof GameLog] as number) || 0
              return sum + val
            }, 0) /
            gamesWithAbsentPlayerPresent.length
          : 0

      // Calculate average stat when absent player is NOT playing
      const withoutStarAvg =
        gamesWithoutAbsentPlayer.length > 0
          ? gamesWithoutAbsentPlayer.reduce((sum, g: GameLog) => {
              const val = (g[statKey as keyof GameLog] as number) || 0
              return sum + val
            }, 0) /
            gamesWithoutAbsentPlayer.length
          : 0

      // Calculate impact percentage
      const impactPct =
        withStarAvg > 0
          ? ((withoutStarAvg - withStarAvg) / withStarAvg) * 100
          : withoutStarAvg > 0
            ? 100
            : 0

      // Only include players who have games in both scenarios
      if (gamesWithAbsentPlayerPresent.length > 0 && gamesWithoutAbsentPlayer.length > 0) {
        // Count unique games (not rows, in case of duplicates)
        const uniqueGamesWithStar = new Set(gamesWithAbsentPlayerPresent.map((g: GameLog) => g.game_id)).size
        const uniqueGamesWithoutStar = new Set(gamesWithoutAbsentPlayer.map((g: GameLog) => g.game_id)).size
        
        impactResults.push({
          player: playerName,
          with_star: Math.round(withStarAvg * 100) / 100,
          without_star: Math.round(withoutStarAvg * 100) / 100,
          impact_pct: Math.round(impactPct * 100) / 100,
          rank: 0, // Will be calculated after sorting
          games_with_star: uniqueGamesWithStar,
          games_without_star: uniqueGamesWithoutStar,
        })
      }
    }

    // Sort by impact percentage (highest first)
    impactResults.sort((a, b) => b.impact_pct - a.impact_pct)

    // Add ranks
    impactResults.forEach((result, index) => {
      result.rank = index + 1
    })

    return NextResponse.json({
      success: true,
      team,
      absent_player,
      stat,
      results: impactResults,
    })
  } catch (error) {
    console.error('Unexpected error in POST:', error)
    return NextResponse.json(
      { error: 'An unexpected error occurred' },
      { status: 500 }
    )
  }
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const action = searchParams.get('action')
    const rawTeam = searchParams.get('team')

    // Validate action
    if (action === 'players') {
      const team = validateTeam(rawTeam)
      if (!team) {
        return NextResponse.json(
          { error: 'Invalid or missing team parameter' },
          { status: 400 }
        )
      }

      const players = PLAYERS_BY_TEAM[team] || []
      return NextResponse.json({
        team,
        players,
        count: players.length,
      })
    }

    // Default: return teams
    const teams = Object.keys(PLAYERS_BY_TEAM)
    return NextResponse.json({
      teams,
      count: teams.length,
    })
  } catch (error) {
    console.error('Unexpected error in GET:', error)
    return NextResponse.json(
      { error: 'An unexpected error occurred' },
      { status: 500 }
    )
  }
}
