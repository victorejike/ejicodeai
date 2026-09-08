'use client';

import useSWR from 'swr';
import { fetcher, ProfileCompletion } from './api';

export interface SessionUser {
  id?: string;
  username: string;
  email: string;
  full_name?: string | null;
  account_type: string;
  organization_id?: string | null;
  organization?: { id: string; name: string; slug: string; plan: string } | null;
  roles?: string[];
  is_active?: boolean;
  is_superuser?: boolean;
}

export interface CandidateProfile {
  id: string;
  user_id: string;
  full_name: string | null;
  title: string | null;
  bio: string | null;
  skills: string[];
  experience_years: number | null;
  experience: any[];
  education: any[];
  portfolio_url: string | null;
  github_url: string | null;
  linkedin_url: string | null;
  resume_url: string | null;
  location: string | null;
  preferred_locations: string[];
  remote_preference: string | null;
  job_types: string[];
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string | null;
  technologies: string[];
  career_goals: string | null;
  ai_candidate_summary: Record<string, any>;
  completion_percentage: number;
  has_cv: boolean;
  onboarding_complete: boolean;
}

export interface Session {
  user: SessionUser | null;
  profile: CandidateProfile | null;
  completion: ProfileCompletion | null;
  /** Preferred greeting name, or null - never a placeholder. */
  firstName: string | null;
  displayName: string | null;
  accountType: string | null;
  /** True once the backend says the agents may run for this user. */
  agentReady: boolean;
  loading: boolean;
  error: unknown;
  /** Human-readable reason the agents are blocked, for button tooltips. */
  gateReason: string | null;
  refresh: () => void;
}

/**
 * Identity + profile completeness, fetched once and shared by every page.
 *
 * Pages used to re-request the profile ad hoc and each derive their own idea of
 * "is this user ready". Both now come from the backend's own completion payload,
 * so the greeting, the checklist and the disabled buttons always agree.
 */
export function useSession(): Session {
  const me = useSWR<SessionUser>('/api/auth/me', fetcher, {
    revalidateOnFocus: false,
    shouldRetryOnError: false,
  });
  const profileRes = useSWR<{ profile: CandidateProfile; profile_completion: ProfileCompletion }>(
    '/api/individual/profile',
    fetcher,
    { revalidateOnFocus: false, shouldRetryOnError: false }
  );

  const completion = profileRes.data?.profile_completion ?? null;
  const user = me.data ?? null;

  return {
    user,
    profile: profileRes.data?.profile ?? null,
    completion,
    firstName: completion?.first_name ?? null,
    displayName: completion?.display_name ?? user?.full_name ?? null,
    accountType: user?.account_type ?? null,
    agentReady: Boolean(completion?.agent_ready),
    loading: (!me.data && !me.error) || (!profileRes.data && !profileRes.error),
    error: me.error ?? profileRes.error ?? null,
    gateReason: completion && !completion.agent_ready ? completion.reasons.join(' ') : null,
    refresh: () => {
      me.mutate();
      profileRes.mutate();
    },
  };
}

export default useSession;
