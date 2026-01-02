'use client';

import { createContext, useContext, useEffect, useState } from 'react';
import { createClient } from '@supabase/supabase-js';
import type { User } from '@supabase/supabase-js';

interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  subscription_tier: 'free' | 'premium' | 'pro';
  stripe_customer_id?: string;
  created_at: string;
  updated_at: string;
}

interface AuthContextType {
  user: User | null;
  profile: UserProfile | null;
  loading: boolean;
  signUp: (email: string, password: string, fullName: string) => Promise<void>;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    let isInitialized = false;

    // Subscribe to auth changes (this handles initial state + ongoing changes)
    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event, session) => {
      if (isMounted) {
        setUser(session?.user || null);

        if (session?.user) {
          const { data: profileData } = await supabase
            .from('profiles')
            .select('*')
            .eq('id', session.user.id)
            .single();

          if (isMounted) {
            setProfile(profileData as UserProfile);
          }
        } else {
          setProfile(null);
        }

        // Set loading to false after first auth state change
        if (!isInitialized) {
          isInitialized = true;
          setLoading(false);
        }
      }
    });

    // Set a timeout to ensure loading stops even if auth state listener doesn't fire
    const timeoutId = setTimeout(() => {
      if (isMounted && !isInitialized) {
        isInitialized = true;
        setLoading(false);
      }
    }, 2000);

    return () => {
      isMounted = false;
      clearTimeout(timeoutId);
      subscription?.unsubscribe();
    };
  }, []);

  const signUp = async (email: string, password: string, fullName: string) => {
    const { data: authData, error: authError } = await supabase.auth.signUp({
      email,
      password,
    });

    if (authError) throw authError;
    if (!authData.user) throw new Error('Signup failed');

    // Create profile via API route (which uses service role key)
    try {
      const response = await fetch('/api/auth/create-profile', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          userId: authData.user.id,
          email,
          fullName,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        console.error('Profile creation failed:', errorData);
        // Don't throw - user is created even if profile creation fails
      }
    } catch (err) {
      console.error('Error creating profile:', err);
      // Don't throw - user is still created
    }
  };

  const signIn = async (email: string, password: string) => {
    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (error) throw error;
  };

  const signOut = async () => {
    try {
      // Sign out from Supabase - use global scope to clear all sessions
      await supabase.auth.signOut({ scope: 'global' });
    } catch (error) {
      console.error('Supabase sign out error:', error);
    } finally {
      // Always clear local state
      setUser(null);
      setProfile(null);
    }
  };

  return (
    <AuthContext.Provider value={{ user, profile, loading, signUp, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
