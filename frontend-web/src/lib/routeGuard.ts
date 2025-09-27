// Centralized protected route rules and helpers

export type RouteRule = {
  name: string;
  pattern: RegExp; // test against location.pathname
  requireAuth: boolean;
  roles?: string[]; // if set, user must have at least one of these roles
};

export const PROTECTED_ROUTES: RouteRule[] = [
  { name: 'chronicle', pattern: /^\/chronicle(\/.*)?$/, requireAuth: true },
  // Add more rules here, e.g.
  // { name: 'profile', pattern: /^\/profile(\/.*)?$/, requireAuth: true },
];

export function isProtectedPath(pathname: string): boolean {
  return PROTECTED_ROUTES.some((r) => r.requireAuth && r.pattern.test(pathname));
}

export function getMatchedRule(pathname: string): RouteRule | null {
  for (const r of PROTECTED_ROUTES) {
    if (r.pattern.test(pathname)) return r;
  }
  return null;
}

export function canAccess(pathname: string, userRoles?: string[] | null): boolean {
  const rule = getMatchedRule(pathname);
  if (!rule) return true; // no rule => public
  if (!rule.requireAuth) return true;
  // require auth: SSR/CSR should have already validated user presence
  if (!userRoles || userRoles.length === 0) return false;
  if (!rule.roles || rule.roles.length === 0) return true; // no specific role required
  return userRoles.some((r) => rule.roles!.includes(r));
}
