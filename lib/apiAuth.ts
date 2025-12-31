import { createClient } from '@supabase/supabase-js'
import { NextRequest, NextResponse } from 'next/server'

/**
 * Verify user authentication using Supabase auth header
 * Returns userId if authenticated, throws error if not
 */
export async function requireAuth(request: NextRequest): Promise<string> {
  const authHeader = request.headers.get('authorization')
  
  if (!authHeader?.startsWith('Bearer ')) {
    throw new Error('UNAUTHORIZED')
  }

  const token = authHeader.slice(7)
  
  // Create Supabase client to verify the token
  const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  )

  const { data, error } = await supabase.auth.getUser(token)

  if (error || !data.user?.id) {
    throw new Error('UNAUTHORIZED')
  }

  return data.user.id
}

/**
 * Create a 401 response for unauthorized access
 */
export function unauthorized() {
  return NextResponse.json(
    { error: 'Unauthorized' },
    { status: 401 }
  )
}

/**
 * Create a 403 response for forbidden access
 */
export function forbidden() {
  return NextResponse.json(
    { error: 'Forbidden' },
    { status: 403 }
  )
}

/**
 * Create a 400 response for bad request
 */
export function badRequest(message: string) {
  return NextResponse.json(
    { error: message },
    { status: 400 }
  )
}

/**
 * Create a 500 response for server error (generic, no details)
 */
export function serverError() {
  return NextResponse.json(
    { error: 'An error occurred processing your request' },
    { status: 500 }
  )
}
