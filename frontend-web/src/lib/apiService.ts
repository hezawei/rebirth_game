// src/lib/apiService.ts

const BACKEND_URL = 'http://127.0.0.1:8000';

// Function to get the token from localStorage
function getToken(): string | null {
    if (typeof window !== 'undefined') {
        return localStorage.getItem('access_token');
    }
    return null;
}

// Main API request function
async function request(endpoint: string, options: RequestInit = {}) {
    const url = `${BACKEND_URL}${endpoint}`;
    const token = getToken();

    // Default headers with explicit type
    const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        ...options.headers as Record<string, string>,
    };

    // Add Authorization header if token exists
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const config: RequestInit = {
        ...options,
        headers,
    };

    try {
        const response = await fetch(url, config);
        if (!response.ok) {
            // Try to parse error message from backend
            const errorData = await response.json().catch(() => ({ detail: response.statusText }));
            throw new Error(errorData.detail || 'An unknown error occurred');
        }
        // If response is OK but has no content
        if (response.status === 204) {
            return null;
        }
        return await response.json();
    } catch (error) {
        console.error('API Service Error:', error);
        throw error;
    }
}

// --- Authentication Endpoints ---

export const api = {
    // POST /auth/register
    register: (email: string, password: string) => {
        return request('/auth/register', {
            method: 'POST',
            body: JSON.stringify({ email, password }),
        });
    },

    // POST /auth/token (Login)
    login: (email: string, password: string) => {
        const formData = new URLSearchParams();
        formData.append('username', email);
        formData.append('password', password);

        return request('/auth/token', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: formData,
        });
    },

    // GET /users/me
    getCurrentUser: () => {
        return request('/users/me');
    },

    // PUT /users/me
    updateProfile: (profileData: { nickname?: string; age?: number; identity?: string }) => {
        return request('/users/me', {
            method: 'PUT',
            body: JSON.stringify(profileData),
        });
    },

    // --- Story Endpoints ---

    // POST /story/start
    startStory: (wish: string) => {
        return request('/story/start', {
            method: 'POST',
            body: JSON.stringify({ wish }),
        });
    },

    // POST /story/continue
    continueStory: (sessionId: number, nodeId: number, choice: string) => {
        return request('/story/continue', {
            method: 'POST',
            body: JSON.stringify({ session_id: sessionId, node_id: nodeId, choice }),
        });
    },

    // --- Chronicle Endpoints ---

    // GET /story/sessions
    getSessions: () => {
        return request('/story/sessions');
    },

    // GET /story/sessions/{sessionId}
    getSessionDetails: (sessionId: number) => {
        return request(`/story/sessions/${sessionId}`);
    },

    // GET /story/sessions/{sessionId}/latest
    getLatestStoryNode: (sessionId: number) => {
        return request(`/story/sessions/${sessionId}/latest`);
    },

    // POST /story/retry
    retryFromNode: (nodeId: number) => {
        return request('/story/retry', {
            method: 'POST',
            body: JSON.stringify({ node_id: nodeId }),
        });
    },
};

// --- Token Management ---

export function setToken(token: string): void {
    if (typeof window !== 'undefined') {
        localStorage.setItem('access_token', token);
    }
}

export function removeToken(): void {
    if (typeof window !== 'undefined') {
        localStorage.removeItem('access_token');
    }
}
