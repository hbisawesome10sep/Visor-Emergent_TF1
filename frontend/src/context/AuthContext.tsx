import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { apiRequest, setTokenExpiredHandler } from '../utils/api';

type User = {
  id: string;
  email: string;
  full_name: string;
  dob: string;
  pan: string;
  aadhaar_last4: string;
  created_at: string;
};

type AuthContextType = {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: any) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextType>({
  user: null,
  token: null,
  loading: true,
  login: async () => {},
  register: async () => {},
  logout: async () => {},
});

export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const logoutCalledRef = useRef(false);

  useEffect(() => {
    loadStoredAuth();
  }, []);

  const loadStoredAuth = async () => {
    try {
      const storedToken = await AsyncStorage.getItem('visor_token');
      const storedUser = await AsyncStorage.getItem('visor_user');
      if (storedToken && storedUser) {
        setToken(storedToken);
        setUser(JSON.parse(storedUser));
      }
    } catch (e) {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  const login = async (email: string, password: string) => {
    const data = await apiRequest('/auth/login', {
      method: 'POST',
      body: { email, password },
    });
    await AsyncStorage.setItem('visor_token', data.token);
    await AsyncStorage.setItem('visor_user', JSON.stringify(data.user));
    setToken(data.token);
    setUser(data.user);
  };

  const register = async (regData: any) => {
    const data = await apiRequest('/auth/register', {
      method: 'POST',
      body: regData,
    });
    await AsyncStorage.setItem('visor_token', data.token);
    await AsyncStorage.setItem('visor_user', JSON.stringify(data.user));
    setToken(data.token);
    setUser(data.user);
  };

  const logout = async () => {
    await AsyncStorage.removeItem('visor_token');
    await AsyncStorage.removeItem('visor_user');
    setToken(null);
    setUser(null);
  };

  // Register token-expired handler for auto-logout (prevents stale token crashes)
  useEffect(() => {
    setTokenExpiredHandler(() => {
      // Prevent multiple logout calls from parallel requests
      if (logoutCalledRef.current) return;
      logoutCalledRef.current = true;
      console.warn('[Auth] Token expired — logging out automatically');
      logout().finally(() => {
        logoutCalledRef.current = false;
      });
    });
  }, []);

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
