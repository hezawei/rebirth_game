import type { Handle } from '@sveltejs/kit';
import { redirect } from '@sveltejs/kit';
import { isProtectedPath, canAccess } from '$lib/routeGuard';

export const handle: Handle = async ({ event, resolve }) => {
  const path = event.url.pathname;

  // Global SSR guard for protected routes
  if (isProtectedPath(path)) {
    const cookieToken = event.cookies.get('access_token');
    if (!cookieToken) {
      throw redirect(302, '/');
    }
    try {
      const me = await event.fetch('/api/users/me', { headers: { accept: 'application/json' } });
      if (!me.ok) throw redirect(302, '/');
      const user = await me.json();
      const roles: string[] | undefined = user?.roles;
      if (!canAccess(path, roles || [])) {
        throw redirect(302, '/');
      }
    } catch {
      throw redirect(302, '/');
    }
  }

  return resolve(event);
};
