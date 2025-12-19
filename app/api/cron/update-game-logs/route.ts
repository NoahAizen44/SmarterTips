import { createClient } from '@supabase/supabase-js'
import { NextRequest, NextResponse } from 'next/server'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
)

// Map of all NBA teams to their IDs for nba_api
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

async function fetchGameLogsFromAPI(teamName: string): Promise<any[]> {
  /**
   * Fetch game logs from nba_api via python microservice or direct API call
   * Since nba_api is Python-only, we'll make requests to stats.nba.com directly
   */
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

    const data = await response.json()
    return data.resultSets?.[0]?.rowSet || []
  } catch (error) {
    console.error(`Error fetching ${teamName}:`, error)
    return []
  }
}

async function updateTeamGameLogs(teamName: string): Promise<number> {
  try {
    console.log(`Updating ${teamName}...`)

    // Get the latest game date in database for this team
    const { data: latest } = await supabase
      .from('player_game_logs')
      .select('game_date')
      .eq('team', teamName)
      .order('game_date', { ascending: false })
      .limit(1)

    const lastGameDate = latest?.[0]?.game_date ? new Date(latest[0].game_date) : new Date('2025-10-01')

    // Fetch new game logs from API
    const newGames = await fetchGameLogsFromAPI(teamName)

    if (newGames.length === 0) {
      console.log(`  No new games found for ${teamName}`)
      return 0
    }

    // Filter for games after the last recorded date and prepare data
    const gamesToInsert: any[] = []

    for (const game of newGames) {
      const gameDate = new Date(game[3]) // Game date is typically in column 3
      if (gameDate <= lastGameDate) continue

      // Map the game data to our schema
      // This depends on the actual nba_api response format
      gamesToInsert.push({
        team: teamName,
        player_id: game[4], // Adjust based on actual column
        player_name: game[5], // Adjust based on actual column
        game_date: game[3],
        game_id: game[2],
        position: game[6] || null,
        pts: game[8] || 0,
        reb: game[9] || 0,
        ast: game[10] || 0,
        '3pm': game[11] || 0,
        '3pa': game[12] || 0,
        stl: game[13] || 0,
        blk: game[14] || 0,
        season: 2025,
      })
    }

    if (gamesToInsert.length === 0) {
      console.log(`  No new games after ${lastGameDate.toISOString().split('T')[0]}`)
      return 0
    }

    // Insert in batches of 100
    let inserted = 0
    for (let i = 0; i < gamesToInsert.length; i += 100) {
      const batch = gamesToInsert.slice(i, i + 100)
      const { error } = await supabase.from('player_game_logs').insert(batch)

      if (error) {
        console.error(`  Error inserting batch for ${teamName}:`, error.message)
      } else {
        inserted += batch.length
        console.log(`  Inserted ${batch.length} records`)
      }
    }

    return inserted
  } catch (error) {
    console.error(`Error updating ${teamName}:`, error)
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
    console.log('Starting game log update cron job...')
    const startTime = Date.now()

    let totalInserted = 0

    // Update each team
    for (const [teamName] of Object.entries(TEAM_IDS)) {
      const inserted = await updateTeamGameLogs(teamName)
      totalInserted += inserted

      // Rate limiting - wait between requests
      await new Promise((resolve) => setTimeout(resolve, 500))
    }

    // Get updated database stats
    const { count: totalRecords } = await supabase
      .from('player_game_logs')
      .select('*', { count: 'exact', head: true })

    const duration = Math.round((Date.now() - startTime) / 1000)

    console.log(`Update complete in ${duration}s. Inserted ${totalInserted} new records.`)

    return NextResponse.json(
      {
        success: true,
        message: 'Game log update completed',
        totalInserted,
        totalRecords,
        durationSeconds: duration,
        timestamp: new Date().toISOString(),
      },
      { status: 200 }
    )
  } catch (error) {
    console.error('Cron job error:', error)
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    )
  }
}
