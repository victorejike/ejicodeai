const API_URL = 'http://localhost:8000';

/**
 * Determine where to send a user right after authenticating.
 *
 * Discovery must never run against an empty or fabricated profile, so a user
 * is only sent to their dashboard once their real knowledge base exists:
 *   - Individual: a CV has been uploaded, or a title + at least one skill saved.
 *   - Enterprise: at least one real talent/client requirement has been created.
 *
 * Otherwise (including on any uncertainty/error) this defaults to the profile
 * setup page rather than guessing the dashboard is safe to show.
 */
export async function resolvePostLoginDestination(
  accountType: string,
  accessToken?: string | null
): Promise<string> {
  const profilePath = accountType === 'enterprise' ? '/enterprise/profile' : '/individual/profile';
  const dashboardPath = accountType === 'enterprise' ? '/enterprise/dashboard' : '/individual/dashboard';

  if (!accessToken) {
    return profilePath;
  }

  try {
    if (accountType === 'enterprise') {
      const res = await fetch(`${API_URL}/v1/enterprise/organization`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      if (res.ok) {
        const data = await res.json();
        if (data?.organization?.onboarding_complete) return dashboardPath;
      }
      return profilePath;
    }

    const res = await fetch('/api/individual/profile', {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    if (res.ok) {
      const data = await res.json();
      if (data?.profile?.onboarding_complete) return dashboardPath;
    }
    return profilePath;
  } catch {
    return profilePath;
  }
}
