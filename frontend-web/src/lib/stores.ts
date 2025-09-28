// src/lib/stores.ts
import { writable } from 'svelte/store';
import { api } from './apiService';

const SESSION_EXPIRY_KEY = 'auth:expires_at';
const DEFAULT_EXPIRES_SECONDS = 3600;
const REFRESH_MARGIN_SECONDS = 300;

let refreshTimer: number | null = null;

function writeExpiry(seconds: number) {
  if (typeof window === 'undefined') return;
  const expiresAt = Date.now() + seconds * 1000;
  sessionStorage.setItem(SESSION_EXPIRY_KEY, String(expiresAt));
}

function clearExpiry() {
  if (typeof window === 'undefined') return;
  sessionStorage.removeItem(SESSION_EXPIRY_KEY);
}

function getRemainingSeconds(): number | null {
  if (typeof window === 'undefined') return null;
  const raw = sessionStorage.getItem(SESSION_EXPIRY_KEY);
  if (!raw) return null;
  const expiresAt = Number(raw);
  if (Number.isNaN(expiresAt)) {
    sessionStorage.removeItem(SESSION_EXPIRY_KEY);
    return null;
  }
  const remainingMs = expiresAt - Date.now();
  if (remainingMs <= 0) {
    sessionStorage.removeItem(SESSION_EXPIRY_KEY);
    return null;
  }
  return Math.floor(remainingMs / 1000);
}

function isReloadNavigation(): boolean {
  if (typeof window === 'undefined' || typeof performance === 'undefined') return false;
  const navEntries = performance.getEntriesByType?.('navigation') as PerformanceNavigationTiming[] | undefined;
  if (navEntries && navEntries.length > 0) {
    const type = navEntries[0].type;
    return type === 'reload' || type === 'back_forward';
  }
  const perfNav = (performance as unknown as { navigation?: { type: number; TYPE_RELOAD?: number; TYPE_BACK_FORWARD?: number } }).navigation;
  if (perfNav) {
    const { type, TYPE_RELOAD, TYPE_BACK_FORWARD } = perfNav;
    if (TYPE_RELOAD !== undefined && type === TYPE_RELOAD) return true;
    if (TYPE_BACK_FORWARD !== undefined && type === TYPE_BACK_FORWARD) return true;
  }
  return false;
}

function stopRefresh(clearKey = true) {
  if (typeof window !== 'undefined' && refreshTimer !== null) {
    window.clearTimeout(refreshTimer);
    refreshTimer = null;
  }
  if (clearKey) {
    clearExpiry();
  }
}

function scheduleRefresh(seconds: number) {
  if (typeof window === 'undefined') return;
  stopRefresh(false);
  writeExpiry(seconds);

  const waitSeconds = Math.max(seconds - REFRESH_MARGIN_SECONDS, 30);
  refreshTimer = window.setTimeout(async () => {
    try {
      const res = await fetch('/api/auth/refresh', { method: 'POST' });
      if (!res.ok) {
        throw new Error('refresh failed');
      }
      // Refresh successful, schedule next cycle with default duration
      scheduleRefresh(DEFAULT_EXPIRES_SECONDS);
    } catch (err) {
      stopRefresh();
      // 通知外部需要重新登录
      window.dispatchEvent(new CustomEvent('auth:refresh-failed', { detail: err }));
    }
  }, waitSeconds * 1000);
}

// Helper for creating a store that syncs with localStorage
function createPersistentStore<T>(key: string, startValue: T) {
  const isBrowser = typeof window !== 'undefined';
  const storedValue = isBrowser ? localStorage.getItem(key) : null;
  const initialValue = storedValue ? JSON.parse(storedValue) : startValue;
  
  const store = writable<T>(initialValue);

  store.subscribe(value => {
    if (isBrowser) {
      localStorage.setItem(key, JSON.stringify(value));
    }
  });

  return store;
}

// Helper for creating a store that syncs with sessionStorage (non-auth purposes)
function createSessionStore<T>(key: string, startValue: T) {
  const isBrowser = typeof window !== 'undefined';
  const storedValue = isBrowser ? sessionStorage.getItem(key) : null;
  const initialValue = storedValue ? JSON.parse(storedValue) : startValue;
  
  const store = writable<T>(initialValue);

  store.subscribe(value => {
    if (isBrowser) {
      if (value === null || value === undefined) {
        sessionStorage.removeItem(key);
      } else {
        sessionStorage.setItem(key, JSON.stringify(value));
      }
    }
  });

  return store;
}

// Define the shape of the user object
interface User {
  id: string;
  email: string;
  nickname: string | null;
  age: number | null;
  identity: string | null;
}

// Create a writable store with an initial value of null (logged out)
const { subscribe, set, update } = writable<User | null>(null);
export const authReady = writable<boolean>(false);

async function initializeUser() {
  if (typeof window === 'undefined') return;

  if (isReloadNavigation()) {
    stopRefresh();
    set(null);
    authReady.set(true);
    return;
  }

  const remaining = getRemainingSeconds();
  if (remaining === null) {
    set(null);
    authReady.set(true);
    return;
  }

  try {
    const user = await api.getCurrentUser();
    set(user);
    scheduleRefresh(Math.max(remaining, 60));
  } catch {
    stopRefresh();
    set(null);
  } finally {
    authReady.set(true);
  }
}

if (typeof window !== 'undefined') {
  window.addEventListener('auth:refresh-failed', () => {
    stopRefresh();
    set(null);
    authReady.set(true);
  });
  window.addEventListener('beforeunload', () => {
    // Clear session-scoped expiry so that refresh/new tab returns to login
    stopRefresh();
  });
}

// Call initialize on app startup
initializeUser();

export const userStore = {
  subscribe,
  login: async (email: string, password: string): Promise<void> => {
    const loginResponse = await api.login(email, password);
    const expiresIn = Number(loginResponse?.expires_in ?? DEFAULT_EXPIRES_SECONDS);
    scheduleRefresh(expiresIn);
    const user = await api.getCurrentUser();
    set(user);
  },
  register: async (email: string, password: string): Promise<void> => {
    await api.register(email, password);
  },
  logout: async (): Promise<void> => {
    try {
      await api.logout();
    } catch {}
    stopRefresh();
    set(null);
  },
  update: (updatedUser: Partial<User>): void => {
    update(currentUser => {
      if (currentUser) {
        return { ...currentUser, ...updatedUser };
      }
      return currentUser;
    });
  }
};

export { SESSION_EXPIRY_KEY };

/**
 * Stores the state of a game session to be restored.
 * This is used by the Chronicle page to pass a specific game state
 * back to the main Game page for a "retry".
 * It uses sessionStorage to survive page reloads.
 */
export const gameStateStore = createSessionStore<any>('gameState', null);

/**
 * Stores the ID of the last active game session, persisted in localStorage.
 * This is used to ask the user if they want to continue their last game.
 */
export const lastSessionStore = createPersistentStore<number | null>('lastActiveSessionId', null);

/**
 * Stores the ID of the owner of the last active game session, persisted in localStorage.
 * This is used to ensure that the last session is scoped to the current user.
 */
export const lastSessionOwnerStore = createPersistentStore<string | null>('lastActiveSessionOwnerId', null);
