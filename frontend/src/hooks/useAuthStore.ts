import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User, Token } from '../types';
import { setTokens, clearTokens } from '../lib/api';

interface AuthState {
  user: User | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  setAuth: (user: User, tokens: Token) => void;
  setUser: (user: User) => void;
  logout: () => void;
  setLoading: (loading: boolean) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      isAuthenticated: false,
      isLoading: true,
      setAuth: (user, tokens) => {
        setTokens(tokens);
        set({ user, accessToken: tokens.access_token, isAuthenticated: true, isLoading: false });
      },
      setUser: (user) => set({ user }),
      logout: () => {
        clearTokens();
        set({ user: null, accessToken: null, isAuthenticated: false });
      },
      setLoading: (isLoading) => set({ isLoading }),
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);