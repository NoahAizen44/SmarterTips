import Stripe from 'stripe';
import { headers } from 'next/headers';
import { NextRequest, NextResponse } from 'next/server';

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY || '');

export async function POST(request: NextRequest) {
  try {
    const { userId } = await request.json();

    if (!userId) {
      return NextResponse.json(
        { error: 'User ID is required' },
        { status: 400 }
      );
    }

    // Get the origin for redirect URLs
    const headersList = headers();
    const origin = headersList.get('origin') || 'http://localhost:3000';

    // Create a Stripe checkout session
    const session = await stripe.checkout.sessions.create({
      payment_method_types: ['card'],
      line_items: [
        {
          price: process.env.STRIPE_PREMIUM_PRICE_ID || 'price_1Sd4Q3Jm3zaGaj15qQ0UWBKe', // Premium product price ID
          quantity: 1,
        },
      ],
      mode: 'subscription',
      success_url: `${origin}/checkout-success?session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: `${origin}/checkout-cancel`,
      customer_email: undefined, // Will be set via metadata
      metadata: {
        userId,
      },
    });

    return NextResponse.json({ url: session.url });
  } catch (error) {
    console.error('Checkout session creation error:', error);
    return NextResponse.json(
      { error: 'Failed to create checkout session' },
      { status: 500 }
    );
  }
}
