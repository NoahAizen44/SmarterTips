import Stripe from 'stripe'
import { headers } from 'next/headers'
import { NextRequest, NextResponse } from 'next/server'
import { requireAuth, badRequest, serverError } from '@/lib/apiAuth'

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY || '')

// Validation helpers
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

    // 3. Extract and validate userId
    const requestedUserId = (body as Record<string, unknown>)?.userId

    if (!isValidUserId(requestedUserId)) {
      return badRequest('Invalid userId format')
    }

    // 4. Security: Users can only create checkouts for themselves
    if (requestedUserId !== authUserId) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 403 }
      )
    }

    // 5. Get the origin for redirect URLs
    const headersList = headers()
    const origin = headersList.get('origin') || 'http://localhost:3000'

    // 6. Create a Stripe checkout session
    const session = await stripe.checkout.sessions.create({
      payment_method_types: ['card'],
      line_items: [
        {
          price: process.env.STRIPE_PREMIUM_PRICE_ID || 'price_1Sd4Q3Jm3zaGaj15qQ0UWBKe',
          quantity: 1,
        },
      ],
      mode: 'subscription',
      success_url: `${origin}/checkout-success?session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: `${origin}/checkout-cancel`,
      customer_email: undefined,
      metadata: {
        userId: requestedUserId,
      },
    })

    return NextResponse.json({ url: session.url })
  } catch (err) {
    if (err instanceof Error && err.message === 'UNAUTHORIZED') {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      )
    }

    console.error('Checkout session creation error:', err)
    return serverError()
  }
}
