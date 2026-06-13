import { create } from 'zustand';
import { authApi } from '@/lib/api';

interface User {
  id: string;
  email: string | null;
  username: string | null;
  is_active: boolean;
  roles: string[];
  permissions: string[];
}

interface AuthState {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (login: string, password: string) => Promise<void>;
  logout: () => void;
  fetchMe: () => Promise<void>;
  hasPermission: (perm: string) => boolean;
  hasRole: (role: string) => boolean;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: localStorage.getItem('access_token'),
  user: null,
  isAuthenticated: !!localStorage.getItem('access_token'),
  isLoading: false,

  login: async (login: string, password: string) => {
    set({ isLoading: true });
    try {
      const res = await authApi.login(login, password);
      const { access_token } = res.data;
      localStorage.setItem('access_token', access_token);
      set({ token: access_token, isAuthenticated: true });
      await get().fetchMe();
    } finally {
      set({ isLoading: false });
    }
  },

  logout: () => {
    localStorage.removeItem('access_token');
    set({ token: null, user: null, isAuthenticated: false });
  },

  fetchMe: async () => {
    try {
      const res = await authApi.me();
      set({ user: res.data });
    } catch {
      get().logout();
    }
  },

  hasPermission: (perm: string) => {
    const { user } = get();
    if (!user) return false;
    return user.permissions.includes(perm) || user.roles.includes('owner') || user.roles.includes('admin');
  },

  hasRole: (role: string) => {
    const { user } = get();
    if (!user) return false;
    return user.roles.includes(role);
  },
}));
