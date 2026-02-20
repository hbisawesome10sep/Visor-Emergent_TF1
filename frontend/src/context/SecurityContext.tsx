import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react';
import { AppState, AppStateStatus, Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as LocalAuthentication from 'expo-local-authentication';
import { useAuth } from './AuthContext';

const INACTIVITY_TIMEOUT_MS = 5 * 60 * 1000; // 5 minutes

// User-specific storage keys
function getStorageKeys(userId: string) {
  return {
    PIN_HASH: `visor_pin_hash_${userId}`,
    BIOMETRIC_ENABLED: `visor_biometric_enabled_${userId}`,
    SECURITY_SETUP_DONE: `visor_security_setup_${userId}`,
    LOCK_ENABLED: `visor_lock_enabled_${userId}`,
  };
}

type SecurityContextType = {
  isLocked: boolean;
  isPinSetup: boolean;
  isBiometricEnabled: boolean;
  isBiometricAvailable: boolean;
  isSecuritySetupDone: boolean;
  securityLoading: boolean;
  unlock: () => void;
  lock: () => void;
  setupPin: (pin: string) => Promise<boolean>;
  verifyPin: (pin: string) => Promise<boolean>;
  changePin: (oldPin: string, newPin: string) => Promise<boolean>;
  toggleBiometric: (enabled: boolean) => Promise<void>;
  completeSecuritySetup: () => Promise<void>;
  authenticateWithBiometric: () => Promise<boolean>;
  resetSecurity: () => Promise<void>;
};

const SecurityContext = createContext<SecurityContextType>({
  isLocked: false,
  isPinSetup: false,
  isBiometricEnabled: false,
  isBiometricAvailable: false,
  isSecuritySetupDone: false,
  securityLoading: true,
  unlock: () => {},
  lock: () => {},
  setupPin: async () => false,
  verifyPin: async () => false,
  changePin: async () => false,
  toggleBiometric: async () => {},
  completeSecuritySetup: async () => {},
  authenticateWithBiometric: async () => false,
  resetSecurity: async () => {},
});

export const useSecurity = () => useContext(SecurityContext);

function simpleHash(pin: string): string {
  let hash = 0;
  for (let i = 0; i < pin.length; i++) {
    const char = pin.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash |= 0;
  }
  return 'H' + Math.abs(hash).toString(36) + pin.length;
}

export function SecurityProvider({ children }: { children: React.ReactNode }) {
  const { token, user } = useAuth();
  const userId = user?.id || '';

  const [securityLoading, setSecurityLoading] = useState(true);
  const [isLocked, setIsLocked] = useState(false);
  const [isPinSetup, setIsPinSetup] = useState(false);
  const [isBiometricEnabled, setIsBiometricEnabled] = useState(false);
  const [isBiometricAvailable, setIsBiometricAvailable] = useState(false);
  const [isSecuritySetupDone, setIsSecuritySetupDone] = useState(false);
  const lastActiveTime = useRef(Date.now());
  const appState = useRef(AppState.currentState);

  // Check biometric availability
  useEffect(() => {
    (async () => {
      if (Platform.OS === 'web') {
        setIsBiometricAvailable(false);
        return;
      }
      const compatible = await LocalAuthentication.hasHardwareAsync();
      const enrolled = await LocalAuthentication.isEnrolledAsync();
      setIsBiometricAvailable(compatible && enrolled);
    })();
  }, []);

  // Load stored security settings for THIS user
  useEffect(() => {
    (async () => {
      if (!userId) {
        // No user logged in — reset state
        setIsPinSetup(false);
        setIsBiometricEnabled(false);
        setIsSecuritySetupDone(false);
        setIsLocked(false);
        setSecurityLoading(false);
        return;
      }
      const keys = getStorageKeys(userId);
      const [pinHash, bioEnabled, setupDone] = await Promise.all([
        AsyncStorage.getItem(keys.PIN_HASH),
        AsyncStorage.getItem(keys.BIOMETRIC_ENABLED),
        AsyncStorage.getItem(keys.SECURITY_SETUP_DONE),
      ]);
      const pinExists = !!pinHash;
      const setupComplete = setupDone === 'true';
      setIsPinSetup(pinExists);
      setIsBiometricEnabled(bioEnabled === 'true');
      setIsSecuritySetupDone(setupComplete);
      // If user already set up security, lock the app on login
      if (setupComplete && pinExists) {
        setIsLocked(true);
      }
      setSecurityLoading(false);
    })();
  }, [userId]);

  // Inactivity timeout — track app state changes
  useEffect(() => {
    if (!token || !isSecuritySetupDone) return;

    const handleAppStateChange = (nextState: AppStateStatus) => {
      if (appState.current === 'active' && nextState.match(/inactive|background/)) {
        lastActiveTime.current = Date.now();
      }
      if (nextState === 'active' && appState.current.match(/inactive|background/)) {
        const elapsed = Date.now() - lastActiveTime.current;
        if (elapsed >= INACTIVITY_TIMEOUT_MS && isPinSetup) {
          setIsLocked(true);
        }
      }
      appState.current = nextState;
    };

    const subscription = AppState.addEventListener('change', handleAppStateChange);
    return () => subscription.remove();
  }, [token, isSecuritySetupDone, isPinSetup]);

  const unlock = useCallback(() => setIsLocked(false), []);
  const lock = useCallback(() => setIsLocked(true), []);

  const setupPin = useCallback(async (pin: string): Promise<boolean> => {
    if (pin.length < 4 || pin.length > 6 || !userId) return false;
    const hash = simpleHash(pin);
    await AsyncStorage.setItem(getStorageKeys(userId).PIN_HASH, hash);
    setIsPinSetup(true);
    return true;
  }, [userId]);

  const verifyPin = useCallback(async (pin: string): Promise<boolean> => {
    if (!userId) return false;
    const storedHash = await AsyncStorage.getItem(getStorageKeys(userId).PIN_HASH);
    if (!storedHash) return false;
    return simpleHash(pin) === storedHash;
  }, [userId]);

  const changePin = useCallback(async (oldPin: string, newPin: string): Promise<boolean> => {
    const valid = await verifyPin(oldPin);
    if (!valid) return false;
    return setupPin(newPin);
  }, [verifyPin, setupPin]);

  const toggleBiometric = useCallback(async (enabled: boolean) => {
    if (!userId) return;
    await AsyncStorage.setItem(getStorageKeys(userId).BIOMETRIC_ENABLED, String(enabled));
    setIsBiometricEnabled(enabled);
  }, [userId]);

  const completeSecuritySetup = useCallback(async () => {
    if (!userId) return;
    await AsyncStorage.setItem(getStorageKeys(userId).SECURITY_SETUP_DONE, 'true');
    setIsSecuritySetupDone(true);
  }, [userId]);

  const authenticateWithBiometric = useCallback(async (): Promise<boolean> => {
    if (Platform.OS === 'web') return false;
    const result = await LocalAuthentication.authenticateAsync({
      promptMessage: 'Unlock Visor',
      cancelLabel: 'Use PIN',
      disableDeviceFallback: true,
    });
    return result.success;
  }, []);

  const resetSecurity = useCallback(async () => {
    if (!userId) return;
    const keys = getStorageKeys(userId);
    await Promise.all([
      AsyncStorage.removeItem(keys.PIN_HASH),
      AsyncStorage.removeItem(keys.BIOMETRIC_ENABLED),
      AsyncStorage.removeItem(keys.SECURITY_SETUP_DONE),
      AsyncStorage.removeItem(keys.LOCK_ENABLED),
    ]);
    setIsPinSetup(false);
    setIsBiometricEnabled(false);
    setIsSecuritySetupDone(false);
    setIsLocked(false);
  }, [userId]);

  return (
    <SecurityContext.Provider
      value={{
        isLocked,
        isPinSetup,
        isBiometricEnabled,
        isBiometricAvailable,
        isSecuritySetupDone,
        securityLoading,
        unlock,
        lock,
        setupPin,
        verifyPin,
        changePin,
        toggleBiometric,
        completeSecuritySetup,
        authenticateWithBiometric,
        resetSecurity,
      }}
    >
      {children}
    </SecurityContext.Provider>
  );
}
