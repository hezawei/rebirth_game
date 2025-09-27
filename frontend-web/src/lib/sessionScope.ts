// Helpers to namespace sessionStorage keys per user to ensure isolation

export const CHRONICLE_SNAPSHOT_KEY = 'chronicle:snapshot';
export const CHRONICLE_RETURN_TO_KEY = 'chronicle:return_to';

function k(userId: string | number, base: string): string {
  return `${base}:${userId}`;
}

export function setSessionScoped(userId: string | number, base: string, value: string) {
  if (typeof window === 'undefined') return;
  sessionStorage.setItem(k(userId, base), value);
}

export function getSessionScoped(userId: string | number, base: string): string | null {
  if (typeof window === 'undefined') return null;
  return sessionStorage.getItem(k(userId, base));
}

export function removeSessionScoped(userId: string | number, base: string) {
  if (typeof window === 'undefined') return;
  sessionStorage.removeItem(k(userId, base));
}
