import { createClient } from '@supabase/supabase-js'
import { NextRequest, NextResponse } from 'next/server'
import { PLAYERS_BY_TEAM } from '@/lib/playersData'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)

interface GameStat {
  player_name: string
  pts: number
  reb: number
  ast: number
  '3pm': number
  '3pa': number
  stl: number
  blk: number
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

interface GameLog {
  player_name: string
  game_id: string
  [key: string]: string | number | null
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { team, absent_player, stat = 'PTS' } = body

    if (!team || !absent_player) {
      return NextResponse.json(
        { error: 'Team and absent_player required' },
        { status: 400 }
      )
    }

    // Get all games for the team
    const { data: gameData, error: gameError } = await supabase
      .from('player_game_logs')
      .select('*')
      .eq('team', team)
      .order('game_date', { ascending: false })

    if (gameError) throw gameError
    if (!gameData || gameData.length === 0) {
      return NextResponse.json(
        { error: `No game data found for ${team}` },
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
    const statKey = stat.toLowerCase() as keyof typeof gameData[0]

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
          ? gamesWithAbsentPlayerPresent.reduce((sum, g: any) => sum + (g[statKey] || 0), 0) /
            gamesWithAbsentPlayerPresent.length
          : 0

      // Calculate average stat when absent player is NOT playing
      const withoutStarAvg =
        gamesWithoutAbsentPlayer.length > 0
          ? gamesWithoutAbsentPlayer.reduce((sum, g: any) => sum + (g[statKey] || 0), 0) /
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
      star_player: absent_player,
      rankings: impactResults,
    })
  } catch (err) {
    const errorMessage = err instanceof Error ? err.message : 'Internal server error'
    console.error(err)
    return NextResponse.json({ error: errorMessage }, { status: 500 })
  }
}

// GET endpoint to fetch teams and players
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const action = searchParams.get('action')
    const team = searchParams.get('team')

    if (action === 'teams') {
      // All 30 NBA teams
      const teams = [
        'Atlanta Hawks',
        'Boston Celtics',
        'Brooklyn Nets',
        'Charlotte Hornets',
        'Chicago Bulls',
        'Cleveland Cavaliers',
        'Dallas Mavericks',
        'Denver Nuggets',
        'Detroit Pistons',
        'Golden State Warriors',
        'Houston Rockets',
        'Indiana Pacers',
        'Los Angeles Clippers',
        'Los Angeles Lakers',
        'Memphis Grizzlies',
        'Miami Heat',
        'Milwaukee Bucks',
        'Minnesota Timberwolves',
        'New Orleans Pelicans',
        'New York Knicks',
        'Oklahoma City Thunder',
        'Orlando Magic',
        'Philadelphia 76ers',
        'Phoenix Suns',
        'Portland Trail Blazers',
        'Sacramento Kings',
        'San Antonio Spurs',
        'Toronto Raptors',
        'Utah Jazz',
        'Washington Wizards',
      ]
      return NextResponse.json({ success: true, teams })
    }

    if (action === 'players' && team) {
      // Get players for a team from hardcoded data (instant loading)
      const players = PLAYERS_BY_TEAM[team as keyof typeof PLAYERS_BY_TEAM] || []
      return NextResponse.json({ success: true, players })
    }

    return NextResponse.json(
      { error: 'Invalid action or missing parameters' },
      { status: 400 }
    )
  } catch (err) {
    const errorMessage = err instanceof Error ? err.message : 'Internal server error'
    console.error('GET error:', errorMessage, err)
    return NextResponse.json({ error: errorMessage }, { status: 500 })
  }
}
