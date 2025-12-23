#!/usr/bin/env node

const { createClient } = require('@supabase/supabase-js');
const https = require('https');

const supabase = createClient(
  'https://vszmsnikixfdakwzuown.supabase.co',
  'sb_secret_A2RLLNm4pOfRRDOI73z8iQ_5e6nwC1b'
);

const TEAM_IDS = {
  'Boston Celtics': 1610612738,
  'Miami Heat': 1610612748,
  'Los Angeles Lakers': 1610612747,
};

async function fetchGames(teamId) {
  return new Promise((resolve) => {
    const url = `https://stats.nba.com/stats/teamgamelogs?TeamID=${teamId}&Season=2025&SeasonType=Regular`;
    
    https.get(url, {
      headers: { 'User-Agent': 'Mozilla/5.0' }
    }, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const json = JSON.parse(data);
          resolve(json.resultSets[0].rowSet || []);
        } catch {
          resolve([]);
        }
      });
    }).on('error', () => resolve([]));
  });
}

async function backfillTeam(teamName) {
  console.log(`Backfilling ${teamName}...`);
  const teamId = TEAM_IDS[teamName];
  
  // Fetch games from API
  const games = await fetchGames(teamId);
  console.log(`  Fetched ${games.length} games`);
  
  if (games.length === 0) return 0;
  
  // Get existing records
  const { data: records } = await supabase
    .from('player_game_logs')
    .select('id, game_id, player_name')
    .eq('team', teamName);
  
  console.log(`  Found ${records?.length || 0} existing records`);
  
  if (!records || records.length === 0) return 0;
  
  // Create lookup map
  const map = {};
  for (const r of records) {
    map[`${r.game_id}-${r.player_name}`] = r.id;
  }
  
  // Update each game
  let updated = 0;
  for (const game of games) {
    const key = `${game[2]}-${game[5]}`;
    if (map[key]) {
      const { error } = await supabase
        .from('player_game_logs')
        .update({
          gp: game[7] || 1,
          ftm: game[13] || 0,
          fta: game[14] || 0,
          fga: game[15] || 0,
          fgm: game[16] || 0,
          min: game[17] || 0,
          tov: game[18] || 0,
          pf: game[19] || 0,
          stl: game[20] || 0,
          blk: game[21] || 0,
          fg_pct: game[22] || 0,
          fg3_pct: game[23] || 0,
          ft_pct: game[24] || 0,
        })
        .eq('id', map[key]);
      
      if (!error) updated++;
    }
  }
  
  console.log(`  Updated ${updated} records`);
  return updated;
}

async function main() {
  console.log('Starting backfill...\n');
  let total = 0;
  
  for (const teamName of Object.keys(TEAM_IDS)) {
    const count = await backfillTeam(teamName);
    total += count;
  }
  
  console.log(`\n✅ Complete! Updated ${total} total records.`);
  process.exit(0);
}

main().catch(err => {
  console.error('Error:', err);
  process.exit(1);
});
