// src/lib/stores.ts
import { writable } from 'svelte/store';
import { api, setToken, removeToken } from './apiService';

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

async function initializeUser() {
  if (typeof window === 'undefined') return;

  const token = localStorage.getItem('access_token');
  if (token) {
    try {
      const user = await api.getCurrentUser();
      set(user);
    } catch (error) {
      console.error('Failed to initialize user:', error);
      removeToken(); // Token is invalid, remove it
      set(null);
    }
  }
}

// Call initialize on app startup
initializeUser();

export const userStore = {
  subscribe,
  login: async (email: string, password: string): Promise<void> => {
    const tokenData = await api.login(email, password);
    setToken(tokenData.access_token);
    const user = await api.getCurrentUser();
    set(user);
  },
  register: async (email: string, password: string): Promise<void> => {
    await api.register(email, password);
    // After registration, we don't log them in automatically.
    // The UI will prompt them to log in.
  },
  logout: (): void => {
    removeToken();
    lastSessionStore.set(null); // Clear last session on logout
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
 */
export const gameStateStore = writable<any>(null);

/**
 * Stores the ID of the last active game session, persisted in localStorage.
 * This is used to ask the user if they want to continue their last game.
 */
export const lastSessionStore = createPersistentStore<number | null>('lastActiveSessionId', null);
