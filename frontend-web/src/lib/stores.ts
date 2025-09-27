// src/lib/stores.ts
import { writable, get } from 'svelte/store';
import { api } from './apiService';

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

// Helper for creating a store that syncs with sessionStorage
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
  set(null);

  // Try to hydrate from HttpOnly cookie
  try {
    const user = await api.getCurrentUser();
    set(user);
  } catch {
    set(null);
  }
  authReady.set(true);

  // Cross-tab single-login enforcement: listen for logout broadcasts
  try {
    window.addEventListener('storage', (e) => {
      if (e.key && e.key.startsWith('auth:logout:')) {
        const targetUserId = e.key.replace('auth:logout:', '');
        const current = get(userStore);
        if (current && current.id === targetUserId) {
          set(null);
          // Clear session-scoped game state
          try {
            lastSessionStore.set(null);
            lastSessionOwnerStore.set(null);
            gameStateStore.set(null);
          } catch {}
        }
      }
    });
  } catch {}
}

// Call initialize on app startup
initializeUser();

export const userStore = {
  subscribe,
  login: async (email: string, password: string): Promise<void> => {
    await api.login(email, password);
    const user = await api.getCurrentUser();
    set(user);
    // Notify other tabs of the same account to logout (targeted by userId)
    try { if (typeof window !== 'undefined') localStorage.setItem(`auth:logout:${user.id}`, String(Date.now())); } catch {}
    // Ensure last session persistence is scoped to the current user
    const lastId = typeof window !== 'undefined' ? localStorage.getItem('lastActiveSessionId') : null;
    const owner = typeof window !== 'undefined' ? localStorage.getItem('lastActiveSessionOwnerId') : null;
    if (lastId && owner !== user.id) {
      lastSessionStore.set(null);
      lastSessionOwnerStore.set(null);
    }
  },
  register: async (email: string, password: string): Promise<void> => {
    await api.register(email, password);
    // After registration, we don't log them in automatically.
    // The UI will prompt them to log in.
  },
  logout: async (): Promise<void> => {
    try {
      // Attempt server-side token invalidation (single logout everywhere)
      await api.logout();
    } catch {}
    try {
      const current = get(userStore);
      if (current && typeof window !== 'undefined') {
        localStorage.setItem(`auth:logout:${current.id}`, String(Date.now()));
      }
    } catch {}
    lastSessionStore.set(null); // Clear last session on logout
    lastSessionOwnerStore.set(null); // Also clear session owner on logout
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
