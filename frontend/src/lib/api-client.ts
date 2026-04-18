import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import Cookies from 'js-cookie';

// ---------------------------------------------------------------------------
// In-memory token store
// ---------------------------------------------------------------------------
// The access token MUST NOT be written to localStorage or any readable cookie
// because those are accessible to any JS running on the page (XSS risk).
// The AuthProvider calls `setInMemoryAccessToken` after a successful login or
// token refresh, and clears it on logout.
// ---------------------------------------------------------------------------

let _accessToken: string | null = null;

/** Called by AuthProvider after login / token refresh. */
export function setInMemoryAccessToken(token: string | null): void {
  _accessToken = token;
}

/** Called by AuthProvider on logout to wipe the in-memory token. */
export function clearInMemoryAccessToken(): void {
  _accessToken = null;
}

const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Track refresh state to avoid infinite loops
let isRefreshing = false;
let pendingRequests: Array<(token: string) => void> = [];

function notifyPending(token: string) {
  pendingRequests.forEach((cb) => cb(token));
  pendingRequests = [];
}

// Request interceptor — attach access token from memory, never from storage
apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (_accessToken && config.headers) {
    config.headers['Authorization'] = `Bearer ${_accessToken}`;
  }
  return config;
});

// Response interceptor — handle 401 with token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;

      // Refresh token lives in a SameSite=Strict cookie scoped to /api/v1/auth/refresh.
      // js-cookie can read it here because this code runs in the browser.
      const refreshToken = Cookies.get('refresh_token');
      if (!refreshToken) {
        handleLogout();
        return Promise.reject(error);
      }

      if (isRefreshing) {
        return new Promise((resolve) => {
          pendingRequests.push((token: string) => {
            if (original.headers) {
              original.headers['Authorization'] = `Bearer ${token}`;
            }
            resolve(apiClient(original));
          });
        });
      }

      isRefreshing = true;

      try {
        const { data } = await axios.post(
          `${process.env.NEXT_PUBLIC_API_URL}/auth/refresh`,
          { refresh_token: refreshToken },
        );
        const newToken: string = data.access_token;

        // Store new access token in memory only — never in localStorage.
        setInMemoryAccessToken(newToken);

        notifyPending(newToken);
        isRefreshing = false;

        if (original.headers) {
          original.headers['Authorization'] = `Bearer ${newToken}`;
        }
        return apiClient(original);
      } catch {
        isRefreshing = false;
        handleLogout();
        return Promise.reject(error);
      }
    }

    return Promise.reject(error);
  }
);

function handleLogout() {
  clearInMemoryAccessToken();
  Cookies.remove('refresh_token', { path: '/api/v1/auth/refresh' });
  Cookies.remove('session_present');
  if (typeof window !== 'undefined') {
    window.location.href = '/auth';
  }
}

export default apiClient;
