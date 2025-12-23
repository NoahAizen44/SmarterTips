import { createClient } from '@supabase/supabase-js'
import { NextRequest, NextResponse } from 'next/server'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
)

// Map of all NBA teams to their IDs
const TEAM_IDS: Record<string, number> = {
  'Atlanta Hawks': 1610612737,
  'Boston Celtics': 1610612738,
  'Brooklyn Nets': 1610612751,
  'Charlotte Hornets': 1610612766,
  'Chicago Bulls': 1610612741,
  'Cleveland Cavaliers': 1610612739,
  'Dallas Mavericks': 1610612742,
  'Denver Nuggets': 1610612743,
  'Detroit Pistons': 1610612765,
  'Golden State Warriors': 1610612744,
  'Houston Rockets': 1610612745,
  'Indiana Pacers': 1610612754,
  'Los Angeles Clippers': 1610612746,
  'Los Angeles Lakers': 1610612747,
  'Memphis Grizzlies': 1610612763,
  'Miami Heat': 1610612748,
  'Milwaukee Bucks': 1610612749,
  'Minnesota Timberwolves': 1610612750,
  'New Orleans Pelicans': 1610612740,
  'New York Knicks': 1610612752,
  'Oklahoma City Thunder': 1610612760,
  'Orlando Magic': 1610612753,
  'Philadelphia 76ers': 1610612755,
  'Phoenix Suns': 1610612756,
  'Portland Trail Blazers': 1610612757,
  'Sacramento Kings': 1610612758,
  'San Antonio Spurs': 1610612759,
  'Toronto Raptors': 1610612761,
  'Utah Jazz': 1610612762,
  'Washington Wizards': 1610612764,
}

interface GameLogRow {
  [key: number]: unknown
}

async function fetchGameLogsFromAPI(teamName: string): Promise<GameLogRow[]> {
  const teamId = TEAM_IDS[teamName]
  if (!teamId) return []

  try {
    const response = await fetch(
      `https://stats.nba.com/stats/teamgamelogs?TeamID=${teamId}&Season=2025&SeasonType=Regular`,
      {
        headers: {
          'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        },
      }
    )

    if (!response.ok) return []

    const data = await response.json() as Record<string, unknown>
    const resultSets = data.resultSets as Array<{rowSet?: GameLogRow[]}>
    return resultSets?.[0]?.rowSet || []
  } catch (error) {
    console.error(`Error fetching ${teamName}:`, error)
    return []
  }
}

async function backfillTeamStats(teamName: string): Promise<number> {
  try {
    console.log(`Backfilling ${teamName}...`)

    // Fetch all game logs from API
    const allGames = await fetchGameLogsFromAPI(teamName)

    if (allGames.length === 0) {
      console.log(`  No games found for ${teamName}`)
      return 0
    }

    // Get all existing records for this team
    const { data: existingRecords } = await supabase
      .from('player_game_logs')
      .select('id, game_id, player_name')
      .eq('team', teamName)

    if (!existingRecords || existingRecords.length === 0) {
      console.log(`  No existing records for ${teamName}`)
      return 0
    }

    // Create a map of game_ids for quick lookup
    const existingGames = new Map(
      existingRecords.map((record) => [
        `${record.game_id}-${record.player_name}`,
        record.id,
      ])
    )

    let updated = 0

    // Process each game from API
    for (const game of allGames) {
      const gameId = game[2]
      const playerName = game[5]
      const key = `${gameId}-${playerName}`

      if (existingGames.has(key)) {
        const recordId = existingGames.get(key)

        // Update the record with new stats
        const { error } = await supabase
          .from('player_game_logs')
          .update({
            gp: game[7] || 1,           // Games Played
            ftm: game[13] || 0,         // Free Throws Made
            fta: game[14] || 0,         // Free Throws Attempted
            fga: game[15] || 0,         // Field Goals Attempted
            fgm: game[16] || 0,         // Field Goals Made
            min: game[17] || 0,         // Minutes Played
            tov: game[18] || 0,         // Turnovers
            pf: game[19] || 0,          // Personal Fouls
            stl: game[20] || 0,         // Steals
            blk: game[21] || 0,         // Blocks
            fg_pct: game[22] || 0,      // Field Goal %
            fg3_pct: game[23] || 0,     // 3-Point %
            ft_pct: game[24] || 0,      // Free Throw %
          })
          .eq('id', recordId)

        if (error) {
          console.error(`  Error updating record ${recordId}:`, error.message)
        } else {
          updated++
        }
      }

      // Rate limiting
      await new Promise((resolve) => setTimeout(resolve, 10))
    }

    console.log(`  Updated ${updated} records for ${teamName}`)
    return updated
  } catch (error) {
    console.error(`Error backfilling ${teamName}:`, error)
    return 0
  }
}

export async function GET(request: NextRequest) {
  // Verify the cron secret for security
  const authHeader = request.headers.get('authorization')
  if (authHeader !== `Bearer ${process.env.CRON_SECRET}`) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  try {
    console.log('Starting backfill of game log stats...')
    const startTime = Date.now()

    let totalUpdated = 0

    // Backfill each team
    for (const [teamName] of Object.entries(TEAM_IDS)) {
      const updated = await backfillTeamStats(teamName)
      totalUpdated += updated

      // Rate limiting
      await new Promise((resolve) => setTimeout(resolve, 500))
    }

    const duration = Math.round((Date.now() - startTime) / 1000)

    console.log(`Backfill complete in ${duration}s. Updated ${totalUpdated} records.`)

    return NextResponse.json(
      {
        success: true,
        message: 'Backfill completed',
        totalUpdated,
        durationSeconds: duration,
        timestamp: new Date().toISOString(),
      },
      { status: 200 }
    )
  } catch (error) {
    console.error('Backfill error:', error)
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    )
  }
}
