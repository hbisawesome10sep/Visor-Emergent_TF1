// /app/frontend/src/context/ExperienceModeContext.tsx
/**
 * Experience Mode Context
 * Manages user experience mode (Essential, Plus, Full) across the app
 */

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { useAuth } from './AuthContext';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL || '';

export type ExperienceMode = 'essential' | 'plus' | 'full';

interface ModeInfo {
  title: string;
  subtitle: string;
  description: string;
  icon: string;
  color: string;
  highlights: string[];
}

interface ModeNudge {
  nudge_id: string;
  suggested_mode: ExperienceMode;
  mode_info: ModeInfo;
  message: string;
  cta: string;
  trigger_reason: string;
}

interface ExperienceModeContextType {
  mode: ExperienceMode;
  modeInfo: ModeInfo | null;
  availableFeatures: Set<string>;
  hiddenFeatures: Set<string>;
  loading: boolean;
  pendingNudge: ModeNudge | null;
  onboardingCompleted: boolean;
  
  // Methods
  isFeatureAvailable: (featureId: string) => boolean;
  setMode: (mode: ExperienceMode, source?: string) => Promise<void>;
  checkFeatureAccess: (featureId: string) => Promise<{ available: boolean; required_mode?: string }>;
  respondToNudge: (accepted: boolean) => Promise<void>;
  dismissNudge: () => void;
  refreshMode: () => Promise<void>;
  completeOnboarding: () => Promise<void>;
  trackBehavior: (eventType: string, data?: Record<string, any>) => Promise<void>;
}

const defaultModeInfo: ModeInfo = {
  title: 'Essential',
  subtitle: 'Just keep it simple',
  description: 'AI does the heavy lifting.',
  icon: 'leaf',
  color: '#10B981',
  highlights: []
};

const ExperienceModeContext = createContext<ExperienceModeContextType | null>(null);

interface Props {
  children: ReactNode;
}

export function ExperienceModeProvider({ children }: Props) {
  const { token, isAuthenticated } = useAuth();
  const [mode, setModeState] = useState<ExperienceMode>('essential');
  const [modeInfo, setModeInfo] = useState<ModeInfo | null>(defaultModeInfo);
  const [availableFeatures, setAvailableFeatures] = useState<Set<string>>(new Set());
  const [hiddenFeatures, setHiddenFeatures] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [pendingNudge, setPendingNudge] = useState<ModeNudge | null>(null);
  const [onboardingCompleted, setOnboardingCompleted] = useState(false);

  const apiRequest = useCallback(async (endpoint: string, options: RequestInit = {}) => {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string> || {})
    };
    
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    const response = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      headers
    });
    
    if (!response.ok) {
      throw new Error(`API Error: ${response.status}`);
    }
    
    return response.json();
  }, [token]);

  const refreshMode = useCallback(async () => {
    if (!token || !isAuthenticated) {
      setLoading(false);
      return;
    }
    
    try {
      const data = await apiRequest('/api/experience/mode');
      setModeState(data.current_mode);
      setModeInfo(data.mode_info);
      setAvailableFeatures(new Set(data.available_features));
      setHiddenFeatures(new Set(data.hidden_features));
      setOnboardingCompleted(data.onboarding_completed);
    } catch (e) {
      console.error('Failed to fetch mode:', e);
      // Default to essential on error
      setModeState('essential');
    } finally {
      setLoading(false);
    }
  }, [token, isAuthenticated, apiRequest]);

  const checkForNudge = useCallback(async () => {
    if (!token || !isAuthenticated) return;
    
    try {
      const data = await apiRequest('/api/experience/nudge');
      if (data.has_nudge) {
        setPendingNudge({
          nudge_id: data.nudge_id,
          suggested_mode: data.suggested_mode,
          mode_info: data.mode_info,
          message: data.message,
          cta: data.cta,
          trigger_reason: data.trigger_reason,
        });
      }
    } catch (e) {
      console.error('Failed to check nudge:', e);
    }
  }, [token, isAuthenticated, apiRequest]);

  useEffect(() => {
    if (isAuthenticated) {
      refreshMode();
      // Check for nudges after initial load
      const nudgeTimer = setTimeout(checkForNudge, 5000);
      // Check for nudges periodically
      const interval = setInterval(checkForNudge, 120000); // Every 2 minutes
      return () => {
        clearTimeout(nudgeTimer);
        clearInterval(interval);
      };
    }
  }, [isAuthenticated, refreshMode, checkForNudge]);

  const isFeatureAvailable = useCallback((featureId: string): boolean => {
    // If not authenticated, default to restricted (Essential mode behavior)
    if (!isAuthenticated || !token) return false;
    // If features haven't loaded yet, default to restricted to prevent showing locked content
    if (availableFeatures.size === 0 && hiddenFeatures.size === 0) return false;
    return availableFeatures.has(featureId);
  }, [availableFeatures, hiddenFeatures, isAuthenticated, token]);

  const setMode = useCallback(async (newMode: ExperienceMode, source = 'manual') => {
    if (!token) return;
    
    try {
      await apiRequest('/api/experience/mode', {
        method: 'PUT',
        body: JSON.stringify({ mode: newMode, source })
      });
      await refreshMode();
    } catch (e) {
      console.error('Failed to update mode:', e);
      throw e;
    }
  }, [token, apiRequest, refreshMode]);

  const checkFeatureAccess = useCallback(async (featureId: string) => {
    if (!token) return { available: false };
    
    try {
      const data = await apiRequest(`/api/experience/features/${featureId}`);
      return { available: data.available, required_mode: data.required_mode };
    } catch (e) {
      return { available: false };
    }
  }, [token, apiRequest]);

  const respondToNudge = useCallback(async (accepted: boolean) => {
    if (!token || !pendingNudge) return;
    
    try {
      await apiRequest(`/api/experience/nudge/${pendingNudge.nudge_id}/respond`, {
        method: 'POST',
        body: JSON.stringify({ accepted })
      });
      if (accepted) {
        await refreshMode();
      }
      setPendingNudge(null);
    } catch (e) {
      console.error('Failed to respond to nudge:', e);
    }
  }, [token, pendingNudge, apiRequest, refreshMode]);

  const dismissNudge = useCallback(() => {
    setPendingNudge(null);
  }, []);

  const completeOnboarding = useCallback(async () => {
    if (!token) return;
    
    try {
      await apiRequest('/api/experience/onboarding-complete', { method: 'POST' });
      setOnboardingCompleted(true);
    } catch (e) {
      console.error('Failed to complete onboarding:', e);
    }
  }, [token, apiRequest]);

  const trackBehavior = useCallback(async (eventType: string, data: Record<string, any> = {}) => {
    if (!token) return;
    
    try {
      await apiRequest('/api/experience/behavior', {
        method: 'POST',
        body: JSON.stringify({ event_type: eventType, data })
      });
    } catch (e) {
      // Silent fail for behavior tracking
    }
  }, [token, apiRequest]);

  return (
    <ExperienceModeContext.Provider value={{
      mode,
      modeInfo,
      availableFeatures,
      hiddenFeatures,
      loading,
      pendingNudge,
      onboardingCompleted,
      isFeatureAvailable,
      setMode,
      checkFeatureAccess,
      respondToNudge,
      dismissNudge,
      refreshMode,
      completeOnboarding,
      trackBehavior,
    }}>
      {children}
    </ExperienceModeContext.Provider>
  );
}

export const useExperienceMode = () => {
  const context = useContext(ExperienceModeContext);
  if (!context) {
    throw new Error('useExperienceMode must be used within ExperienceModeProvider');
  }
  return context;
};

export default ExperienceModeContext;
