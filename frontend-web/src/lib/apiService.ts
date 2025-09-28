// src/lib/apiService.ts

const BACKEND_URL = '/api';

// Single auth scheme: HttpOnly cookie set by backend. No in-memory token.

// Main API request function
async function request(endpoint: string, options: RequestInit = {}) {
    const url = `${BACKEND_URL}${endpoint}`;

    // Default headers with explicit type
    const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        ...options.headers as Record<string, string>,
    };

    // Cookies will be automatically sent for same-origin requests

    const config: RequestInit = {
        ...options,
        headers,
    };

    try {
        console.log('[api] request start', { url, method: (options.method || 'GET') });
        const response = await fetch(url, config);
        if (response.status === 401) {
            // Token invalid or logged in elsewhere: clear local token locally and error out
            const errorData = await response.json().catch(() => ({ detail: '登录状态已失效，请重新登录' }));
            console.warn('[api] 401 unauthorized', { url, errorData });
            throw new Error(errorData.detail || '登录状态已失效，请重新登录');
        }
        if (!response.ok) {
            // Try to parse error message from backend
            const errorData = await response.json().catch(() => ({ detail: response.statusText }));
            console.warn('[api] non-OK response', { url, status: response.status, errorData });
            throw new Error(errorData.detail || 'An unknown error occurred');
        }
        // If response is OK but has no content
        if (response.status === 204) {
            console.log('[api] 204 no content', { url });
            return null;
        }
        const data = await response.json();
        console.log('[api] response ok', { url, status: response.status, data });
        return data;
    } catch (error) {
        console.error('[api] error', { url, error });
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

    // POST /auth/logout
    logout: () => {
        return request('/auth/logout', { method: 'POST' });
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

    // POST /story/check_wish
    checkWish: (wish: string) => {
        return request('/story/check_wish', {
            method: 'POST',
            body: JSON.stringify({ wish }),
        });
    },

    // POST /story/prepare_start
    prepareStart: (wish: string) => {
        return request('/story/prepare_start', {
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

    // --- Story Saves ---

    // POST /story/saves
    createSave: (sessionId: number, nodeId: number, title: string) => {
        return request('/story/saves', {
            method: 'POST',
            body: JSON.stringify({ session_id: sessionId, node_id: nodeId, title }),
        });
    },

    // GET /story/saves
    listSaves: (status?: string) => {
        const query = status ? `?status_filter=${encodeURIComponent(status)}` : '';
        return request(`/story/saves${query}`);
    },

    // GET /story/saves/{id}
    getSaveDetail: (saveId: number) => {
        return request(`/story/saves/${saveId}`);
    },

    // PATCH /story/saves/{id}
    updateSave: (saveId: number, payload: { title?: string; status?: string }) => {
        return request(`/story/saves/${saveId}`, {
            method: 'PATCH',
            body: JSON.stringify(payload),
        });
    },

    // DELETE /story/saves/{id}
    deleteSave: (saveId: number) => {
        return request(`/story/saves/${saveId}`, {
            method: 'DELETE',
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

    // GET /story/latest (latest across all sessions for current user)
    getUserLatestNode: () => {
        return request('/story/latest');
    },

    // POST /story/retry
    retryFromNode: (nodeId: number) => {
        return request('/story/retry', {
            method: 'POST',
            body: JSON.stringify({ node_id: nodeId }),
        });
    },
};

// No token management on the client. Auth is fully handled by HttpOnly cookie.
