import Stripe from 'stripe';
import { createClient } from '@supabase/supabase-js';
import { headers } from 'next/headers';
import { NextRequest, NextResponse } from 'next/server';

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY || '');

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
);

export async function POST(request: NextRequest) {
  const body = await request.text();
  const sig = headers().get('stripe-signature');

  if (!sig) {
    console.error('No stripe-signature header found');
    return NextResponse.json(
      { error: 'No stripe-signature header' },
      { status: 400 }
    );
  }

  let event: Stripe.Event;

  try {
    // Verify the webhook signature
    event = stripe.webhooks.constructEvent(
      body,
      sig,
      process.env.STRIPE_WEBHOOK_SECRET || ''
    );
  } catch (err) {
    console.error('Webhook signature verification failed:', err);
    return NextResponse.json(
      { error: `Webhook Error: ${err instanceof Error ? err.message : 'Unknown error'}` },
      { status: 400 }
    );
  }

  // Handle the event
  try {
    switch (event.type) {
      case 'checkout.session.completed': {
        const session = event.data.object as Stripe.Checkout.Session;

        // Get the user ID from metadata
        const userId = session.metadata?.userId;
        if (!userId) {
          console.error('No userId in session metadata');
          return NextResponse.json(
            { error: 'No userId in metadata' },
            { status: 400 }
          );
        }

        // Update the user's subscription tier in Supabase
        const { error } = await supabase
          .from('profiles')
          .update({ subscription_tier: 'premium' })
          .eq('id', userId);

        if (error) {
          console.error('Error updating subscription tier:', error);
          return NextResponse.json(
            { error: 'Failed to update subscription' },
            { status: 500 }
          );
        }

        console.log(`✅ User ${userId} upgraded to premium`);
        break;
      }

      case 'customer.subscription.deleted': {
        const subscription = event.data.object as Stripe.Subscription;

        // Get the customer ID and find the user
        const customerId = subscription.customer as string;

        // Find the user by stripe_customer_id and downgrade them
        const { error } = await supabase
          .from('profiles')
          .update({ subscription_tier: 'free' })
          .eq('stripe_customer_id', customerId);

        if (error) {
          console.error('Error downgrading subscription:', error);
          return NextResponse.json(
            { error: 'Failed to downgrade subscription' },
            { status: 500 }
          );
        }

        console.log(`⬇️ Customer ${customerId} downgraded to free`);
        break;
      }

      default:
        console.log(`Unhandled event type: ${event.type}`);
    }
  } catch (err) {
    console.error('Error processing webhook:', err);
    return NextResponse.json(
      { error: 'Failed to process webhook' },
      { status: 500 }
    );
  }

  return NextResponse.json({ received: true });
}
