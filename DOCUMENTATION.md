# NBA Defense Rankings Platform - Complete Documentation

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Technology Stack](#technology-stack)
4. [Project Structure](#project-structure)
5. [Components](#components)
6. [Database Schema](#database-schema)
7. [API Routes](#api-routes)
8. [Authentication Flow](#authentication-flow)
9. [Data Flow](#data-flow)
10. [Deployment](#deployment)
11. [Future Enhancements](#future-enhancements)

---

## Overview

**NBA Defense Rankings** is a SaaS platform for analyzing NBA team defensive performance across positions and statistics. Users can:
- View defensive stats broken down by position (PG, SG, SF, PF, C)
- Compare multiple teams side-by-side
- Sort by ranking or percentage difference from league average
- Subscribe to premium tiers for advanced features

**Key Features:**
- ✅ Multi-team comparison
- ✅ Real-time ranking calculations
- ✅ User authentication & accounts
- ✅ Subscription tier management
- ✅ Responsive design
- ✅ Dark theme UI

---

## Architecture

### System Overview

```
┌─────────────────┐
│   Frontend      │
│  (Next.js UI)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Next.js API    │
│   (/api/*)      │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│  Supabase Backend       │
│  (Auth + Database)      │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  PostgreSQL Database    │
│  (nba_stats, profiles)  │
└─────────────────────────┘
```

### Core Data Flow

1. **User Authentication** → Supabase Auth
2. **User Query** → Frontend sends team/stat selection
3. **API Processing** → Next.js calculates rankings
4. **Database Query** → Supabase returns stats
5. **Results Display** → Formatted table with rankings

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Next.js 14 (React) | UI, routing, client logic |
| **Styling** | Tailwind CSS | Responsive dark theme |
| **Backend** | Next.js API Routes | Rankings calculation |
| **Database** | Supabase (PostgreSQL) | Data storage |
| **Authentication** | Supabase Auth | User accounts & sessions |
| **State Management** | React Context | User auth state |
| **Type Safety** | TypeScript | Type checking |
| **Data Source** | CSV → Import Script | Initial data loading |
| **Deployment** | Vercel (planned) | Production hosting |

---

## Project Structure

```
nba-betting-tools/
├── app/
│   ├── api/
│   │   └── rankings/
│   │       └── route.ts              # POST /api/rankings endpoint
│   ├── lib/
│   │   └── auth-context.tsx          # Auth provider & hooks
│   ├── login/
│   │   └── page.tsx                  # Login page
│   ├── signup/
│   │   └── page.tsx                  # Sign up page
│   ├── page.tsx                      # Main rankings dashboard
│   ├── layout.tsx                    # Root layout with AuthProvider
│   ├── globals.css                   # Tailwind styles
│   └── fonts/                        # Custom fonts
├── import_data.py                    # CSV to Supabase importer
├── package.json                      # Dependencies
├── tsconfig.json                     # TypeScript config
├── tailwind.config.ts                # Tailwind config
└── .env.local                        # Environment variables
```

---

## Components

### 1. **Authentication Context** (`app/lib/auth-context.tsx`)

**Purpose:** Centralized user auth state management

**Exports:**
- `AuthProvider` - Wraps app, enables auth features
- `useAuth()` - Hook to access auth state

**Features:**
- User session detection
- Sign up with email/password
- Sign in with email/password
- Sign out
- Profile auto-creation
- Auth state subscriptions

**User Profile Attached:**
```typescript
{
  id: string;
  email: string;
  full_name: string;
  subscription_tier: 'free' | 'premium' | 'pro';
  stripe_customer_id?: string;
  created_at: string;
  updated_at: string;
}
```

### 2. **Login Page** (`app/login/page.tsx`)

**Purpose:** User sign-in interface

**Features:**
- Email/password input
- Error handling
- Redirect to dashboard on success
- Link to sign up
- Message display from query params

**Flow:**
1. User enters email + password
2. `signIn()` called from auth context
3. On success → redirects to `/` (dashboard)
4. On error → displays error message

### 3. **Sign Up Page** (`app/signup/page.tsx`)

**Purpose:** New user account creation

**Features:**
- Full name, email, password input
- Email validation
- Password requirements (6+ chars)
- Auto-profile creation in Supabase
- Success message with redirect to login

**Flow:**
1. User fills: name, email, password
2. `signUp()` called
3. Supabase Auth user created
4. Profile record inserted in DB
5. Success message shows
6. Redirects to login after 2s

### 4. **Rankings Dashboard** (`app/page.tsx`)

**Purpose:** Main application interface for analysis

**Controls:**
- **Team Selection:** Checkboxes for all 30 NBA teams
- **Time Period:** Radio buttons (2025-26, Last 15, Last 7)
- **Stats Display:** Checkboxes (PTS, REB, AST, 3PM, STL, BLK)
- **Sort By:** Radio buttons (Best Rank, Highest Difference %)

**Results Display:**
- Team column (which team)
- Stat column (which statistic)
- Position column (PG, SG, SF, PF, C)
- Value column (actual stat value)
- vs Avg column (% difference, color-coded)
- Rank column (X/30 position)

**Features:**
- Multi-team selection
- Real-time sorting
- Color-coded performance (green = above avg, red = below)
- Error handling
- Loading states
- User info display (top-right)
- Sign out button

---

## Database Schema

### Table: `nba_stats`

**Purpose:** Store all NBA defensive statistics

```sql
CREATE TABLE nba_stats (
  id INT PRIMARY KEY AUTO_INCREMENT,
  team TEXT NOT NULL,                    -- Team name (e.g., "Atlanta")
  position TEXT NOT NULL,                -- Position (PG, SG, SF, PF, C)
  stat_name TEXT NOT NULL,               -- Stat (PTS, REB, AST, 3PM, STL, BLK)
  value NUMERIC NOT NULL,                -- Actual stat value (decimal)
  time_period TEXT NOT NULL,             -- Period (2025-26, Last 15, Last 7)
  scraped_at TIMESTAMP DEFAULT NOW()     -- When data was imported
);
```

**Indexes:**
- `(time_period)` - Optimize dashboard queries
- `(team, time_period)` - Optimize multi-team lookups

**Data Volume:**
- 30 teams × 5 positions × 6 stats × 3 time periods = 2,700 rows

### Table: `profiles`

**Purpose:** User account information linked to Supabase Auth

```sql
CREATE TABLE profiles (
  id UUID PRIMARY KEY,                   -- Links to auth.users.id
  email TEXT NOT NULL UNIQUE,
  full_name TEXT,
  subscription_tier TEXT DEFAULT 'free', -- free, premium, pro
  stripe_customer_id TEXT,               -- For Stripe integration
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

### Table: `subscriptions` (Future Use)

```sql
CREATE TABLE subscriptions (
  id INT PRIMARY KEY AUTO_INCREMENT,
  user_id UUID NOT NULL REFERENCES profiles(id),
  tier TEXT NOT NULL,                    -- Subscription level
  stripe_subscription_id TEXT,
  renewal_date TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);
```

---

## API Routes

### POST `/api/rankings`

**Purpose:** Calculate and return team defensive rankings

**Request Body:**
```typescript
{
  team: string;                    // Single team name (loops in frontend)
  selected_stats: string[];        // Stats to include (PTS, REB, etc.)
  time_period: string;             // 2025-26, Last 15, or Last 7
}
```

**Response:**
```typescript
{
  team: string;
  time_period: string;
  results: [
    {
      team: string;                // Which team (repeated in all results)
      stat: string;                // Which stat
      position: string;            // Which position
      value: number;               // The stat value
      pct_diff: number;            // % diff from league average
      rank: number;                // Ranking (1 = best)
      total_teams: number;         // Always 30
    },
    // ... more results
  ]
}
```

**Algorithm:**
1. Query Supabase for all teams' stats for the time period
2. Group by position
3. For each selected stat:
   - Calculate league average for that position
   - Calculate percentage difference from average
   - Rank team among all 30 (1 = highest stat)
4. Sort by selected sort option
5. Return top 20 results

**Security:**
- Currently public (will add subscription checks later)
- No authentication required (planned: add tier checks)

---

## Authentication Flow

### Sign Up Flow

```
User fills signup form
    ↓
Frontend calls signUp(email, password, name)
    ↓
Supabase Auth creates user account
    ↓
Frontend creates profile record
    ↓
Profile defaults to "free" tier
    ↓
Redirect to login with confirmation message
```

### Sign In Flow

```
User fills login form
    ↓
Frontend calls signIn(email, password)
    ↓
Supabase Auth validates credentials
    ↓
Session established (stored in browser)
    ↓
useAuth hook detects session change
    ↓
Profile fetched from database
    ↓
Redirect to dashboard
```

### Protected Content

```
User navigates to /
    ↓
Check if useAuth().user exists
    ↓
If not → Redirect to /login
    ↓
If yes → Show dashboard with user profile
```

---

## Data Flow

### Query Execution Flow

```
1. USER INTERACTION
   User selects teams, stats, period, sort option
   ↓
2. FORM SUBMISSION
   Frontend loops through each selected team
   ↓
3. API CALL (per team)
   POST /api/rankings with team + stats + period
   ↓
4. BACKEND PROCESSING
   a) Query Supabase for all 30 teams' stats
   b) Filter by time_period
   c) Pivot data (rows → columns by stat)
   d) For each position:
      - Calculate league average
      - Calculate % difference
      - Determine rank
   ↓
5. RESPONSE
   Return array of results with rankings
   ↓
6. AGGREGATE (Frontend)
   Combine results from all selected teams
   Sort by selected sort option
   ↓
7. DISPLAY
   Render table with Team, Stat, Pos, Value, %, Rank columns
```

### Data Transformation Example

**Raw Database:**
```
team: "Atlanta", position: "PG", stat_name: "PTS", value: 27.27
team: "Atlanta", position: "PG", stat_name: "REB", value: 7.12
team: "Boston", position: "PG", stat_name: "PTS", value: 23.48
...
```

**After Pivot (for PG position):**
```
{
  team: "Atlanta",
  position: "PG",
  pts: 27.27,      // stat_name: "PTS" → lowercase pts
  reb: 7.12,       // stat_name: "REB" → lowercase reb
  ast: 8.88,
  3pm: 3.50,       // stat_name: "3PM" → lowercase 3pm
  stl: 2.06,
  blk: 0.66
}
```

**After Ranking (PTS, PG position):**
```
{
  team: "Atlanta",
  stat: "PTS",
  position: "PG",
  value: 27.27,
  pct_diff: +3.35,          // (27.27 - avg) / avg * 100
  rank: 2,                  // 2nd best among 30 teams
  total_teams: 30
}
```

---

## Deployment

### Current Status
- ✅ Development: Running on `http://localhost:3000`
- ⏳ Production: Ready for Vercel deployment

### Prerequisites for Deployment
1. GitHub repository connected
2. Vercel account
3. Environment variables configured

### Environment Variables Required

**.env.local** (development)
```
NEXT_PUBLIC_SUPABASE_URL=https://vszmsnikixfdakwzuown.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Deployment Steps (To Do)

1. Push code to GitHub
2. Connect repo to Vercel
3. Set environment variables in Vercel
4. Deploy
5. Configure custom domain (optional)

### Post-Deployment

- Enable email confirmation in Supabase Auth
- Set up password reset emails
- Configure allowed domains
- Monitor performance
- Set up CI/CD for automated deployments

---

## Future Enhancements

### Phase 2: Payments & Subscriptions
- [ ] Integrate Stripe for payments
- [ ] Create subscription products (Free, Premium, Pro)
- [ ] Add payment checkout flow
- [ ] Restrict features by subscription tier
- [ ] Implement usage tracking

### Phase 3: Additional Tools
- [ ] Teammate Impact Tool
- [ ] Line Comparison Tool
- [ ] Advanced Filtering
- [ ] Custom Date Ranges
- [ ] Export to CSV/PDF

### Phase 4: Advanced Features
- [ ] User dashboards & saved analyses
- [ ] Notification system
- [ ] API for third-party integrations
- [ ] Mobile app
- [ ] Dark mode toggle (currently dark only)

### Phase 5: Automation
- [ ] Nightly scraper (GitHub Actions)
- [ ] Automated data updates
- [ ] Email reports
- [ ] Webhook integrations

---

## Environment Setup

### Local Development

**Prerequisites:**
- Node.js 18+
- npm or yarn
- Git

**Setup:**
```bash
# Clone repo
git clone [repo-url]
cd nba-betting-tools

# Install dependencies
npm install

# Copy environment variables
cp .env.example .env.local

# Start dev server
npm run dev

# Visit http://localhost:3000
```

**Import Test Data:**
```bash
python3 import_data.py
```

---

## Troubleshooting

### Issue: "Supabase RLS blocking queries"
**Solution:** Disable RLS on nba_stats table or create proper RLS policies

### Issue: "Auth context not working"
**Solution:** Ensure `AuthProvider` wraps entire app in `layout.tsx`

### Issue: "Team not showing in results"
**Solution:** Verify team name matches database exactly (e.g., "LA Clippers" not "LA Lakers")

### Issue: "Dev server won't start"
**Solution:** Kill node process and restart: `killall node && npm run dev`

---

## Key Files Reference

| File | Purpose | Key Functions |
|------|---------|---------------|
| `auth-context.tsx` | Auth state management | `useAuth()`, `AuthProvider` |
| `page.tsx` | Main dashboard | Rankings display & filtering |
| `login/page.tsx` | Login UI | User sign-in |
| `signup/page.tsx` | Sign up UI | New user registration |
| `route.ts` (/api/rankings) | Rankings calculation | Ranking algorithm |
| `import_data.py` | Data import | CSV → Supabase |
| `layout.tsx` | Root layout | App structure |

---

## Contact & Support

For questions about the architecture or implementation, refer to:
- Next.js Documentation: https://nextjs.org/docs
- Supabase Documentation: https://supabase.com/docs
- Tailwind CSS: https://tailwindcss.com/docs

---

**Last Updated:** December 11, 2025
**Status:** MVP Complete - Ready for Enhancement
