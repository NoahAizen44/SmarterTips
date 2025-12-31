import { createClient } from '@supabase/supabase-js'
import { NextRequest, NextResponse } from 'next/server'
import { requireAuth, badRequest, serverError, forbidden } from '@/lib/apiAuth'

// Create a Supabase client with service role key (for server-side operations)
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!,
  {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  }
)

// Validation helpers
function isValidEmail(email: unknown): email is string {
  if (typeof email !== 'string') return false
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailRegex.test(email) && email.length <= 255
}

function isValidFullName(fullName: unknown): fullName is string {
  if (typeof fullName !== 'string') return false
  if (fullName.length < 1 || fullName.length > 100) return false
  return /^[a-zA-Z\s\-']+$/.test(fullName)
}

function isValidUserId(userId: unknown): userId is string {
  if (typeof userId !== 'string') return false
  return /^[a-zA-Z0-9_-]+$/.test(userId) && userId.length > 0 && userId.length <= 255
}

export async function POST(request: NextRequest) {
  try {
    // 1. Verify the user is authenticated
    const authUserId = await requireAuth(request)

    // 2. Parse request body
    let body: unknown
    try {
      body = await request.json()
    } catch {
      return badRequest('Invalid JSON in request body')
    }

    // 3. Extract and validate inputs
    const rawUserId = (body as Record<string, unknown>)?.userId
    const rawEmail = (body as Record<string, unknown>)?.email
    const rawFullName = (body as Record<string, unknown>)?.fullName

    if (!isValidUserId(rawUserId)) {
      return badRequest('Invalid userId format')
    }

    if (!isValidEmail(rawEmail)) {
      return badRequest('Invalid email format')
    }

    if (!isValidFullName(rawFullName)) {
      return badRequest('Invalid full name format')
    }

    // 4. Security: Verify the userId matches the authenticated user
    if (rawUserId !== authUserId) {
      return forbidden()
    }

    // 5. Create profile with service role
    const { data, error } = await supabase
      .from('profiles')
      .insert([
        {
          id: rawUserId,
          email: rawEmail,
          full_name: rawFullName,
          subscription_tier: 'free',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ])
      .select()

    if (error) {
      console.error('Profile creation error:', error)
      return serverError()
    }

    return NextResponse.json({ profile: data })
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
