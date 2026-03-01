import React, { useState } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity, Platform,
  Dimensions, StatusBar, Alert,
} from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useSecurity } from '../context/SecurityContext';
import { useTheme } from '../context/ThemeContext';

const { width: SCREEN_WIDTH } = Dimensions.get('window');
const PIN_LENGTH = 4;
const DIAL_SIZE = Math.min(SCREEN_WIDTH * 0.2, 75);

type Step = 'intro' | 'create_pin' | 'confirm_pin' | 'biometric' | 'done';

export function SecuritySetupScreen() {
  const { setupPin, toggleBiometric, completeSecuritySetup, isBiometricAvailable, authenticateWithBiometric } = useSecurity();
  const { colors, isDark } = useTheme();
  const insets = useSafeAreaInsets();

  const [step, setStep] = useState<Step>('intro');
  const [pin, setPin] = useState('');
  const [firstPin, setFirstPin] = useState('');
  const [error, setError] = useState('');

  const handleDigit = (digit: string) => {
    if (pin.length >= PIN_LENGTH) return;
    const newPin = pin + digit;
    setPin(newPin);
    setError('');

    if (newPin.length === PIN_LENGTH) {
      if (step === 'create_pin') {
        setFirstPin(newPin);
        setPin('');
        setStep('confirm_pin');
      } else if (step === 'confirm_pin') {
        if (newPin === firstPin) {
          handlePinConfirmed(newPin);
        } else {
          setError('PINs do not match. Try again.');
          setPin('');
          setFirstPin('');
          setStep('create_pin');
        }
      }
    }
  };

  const handlePinConfirmed = async (confirmedPin: string) => {
    const success = await setupPin(confirmedPin);
    if (success) {
      if (isBiometricAvailable && Platform.OS !== 'web') {
        setStep('biometric');
      } else {
        await completeSecuritySetup();
      }
    }
  };

  const handleEnableBiometric = async () => {
    const success = await authenticateWithBiometric();
    if (success) {
      await toggleBiometric(true);
    }
    await completeSecuritySetup();
  };

  const handleSkipBiometric = async () => {
    await completeSecuritySetup();
  };

  const handleDelete = () => {
    setPin(p => p.slice(0, -1));
    setError('');
  };

  const handleSkipSetup = async () => {
    await completeSecuritySetup();
  };

  // Intro Screen
  if (step === 'intro') {
    return (
      <View style={[styles.container, { backgroundColor: isDark ? '#000' : '#F8F9FA', paddingTop: insets.top }]}>
        <StatusBar barStyle={isDark ? 'light-content' : 'dark-content'} />
        <View style={styles.introContent}>
          <LinearGradient colors={['#10B981', '#059669']} style={styles.introIcon}>
            <MaterialCommunityIcons name="shield-check" size={48} color="#fff" />
          </LinearGradient>
          <Text style={[styles.introTitle, { color: colors.textPrimary }]}>Secure Your Data</Text>
          <Text style={[styles.introSubtitle, { color: colors.textSecondary }]}>
            Set up a PIN and biometric lock to protect your financial data. Your app will lock after 5 minutes of inactivity.
          </Text>

          <View style={styles.featureList}>
            {[
              { icon: 'lock', text: '4-digit PIN lock' },
              { icon: 'fingerprint', text: 'Biometric authentication' },
              { icon: 'timer-sand', text: 'Auto-lock after 5 min' },
              { icon: 'database-lock', text: 'Encrypted data storage' },
            ].map((f, i) => (
              <View key={i} style={[styles.featureRow, { backgroundColor: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.02)' }]}>
                <View style={[styles.featureIcon, { backgroundColor: isDark ? 'rgba(16,185,129,0.15)' : 'rgba(16,185,129,0.1)' }]}>
                  <MaterialCommunityIcons name={f.icon as any} size={20} color="#10B981" />
                </View>
                <Text style={[styles.featureText, { color: colors.textPrimary }]}>{f.text}</Text>
              </View>
            ))}
          </View>

          <TouchableOpacity style={styles.setupBtn} onPress={() => setStep('create_pin')} data-testid="start-setup-btn">
            <LinearGradient colors={['#10B981', '#059669']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={styles.setupBtnGradient}>
              <MaterialCommunityIcons name="shield-lock" size={20} color="#fff" />
              <Text style={styles.setupBtnText}>Set Up PIN</Text>
            </LinearGradient>
          </TouchableOpacity>

          <TouchableOpacity style={styles.skipBtn} onPress={handleSkipSetup} data-testid="skip-setup-btn">
            <Text style={[styles.skipBtnText, { color: colors.textSecondary }]}>Skip for now</Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  }

  // Biometric Setup
  if (step === 'biometric') {
    return (
      <View style={[styles.container, { backgroundColor: isDark ? '#000' : '#F8F9FA', paddingTop: insets.top }]}>
        <StatusBar barStyle={isDark ? 'light-content' : 'dark-content'} />
        <View style={styles.introContent}>
          <LinearGradient colors={['#3B82F6', '#2563EB']} style={styles.introIcon}>
            <MaterialCommunityIcons name="fingerprint" size={48} color="#fff" />
          </LinearGradient>
          <Text style={[styles.introTitle, { color: colors.textPrimary }]}>Enable Biometric</Text>
          <Text style={[styles.introSubtitle, { color: colors.textSecondary }]}>
            Use fingerprint or Face ID for quick access. You can always use your PIN as a fallback.
          </Text>

          <TouchableOpacity style={styles.setupBtn} onPress={handleEnableBiometric} data-testid="enable-biometric-btn">
            <LinearGradient colors={['#3B82F6', '#2563EB']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={styles.setupBtnGradient}>
              <MaterialCommunityIcons name="fingerprint" size={20} color="#fff" />
              <Text style={styles.setupBtnText}>Enable Biometric</Text>
            </LinearGradient>
          </TouchableOpacity>

          <TouchableOpacity style={styles.skipBtn} onPress={handleSkipBiometric} data-testid="skip-biometric-btn">
            <Text style={[styles.skipBtnText, { color: colors.textSecondary }]}>Skip</Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  }

  // PIN Entry (create or confirm)
  const dialPad = [
    ['1', '2', '3'],
    ['4', '5', '6'],
    ['7', '8', '9'],
    ['', '0', 'del'],
  ];

  return (
    <View style={[styles.container, { backgroundColor: isDark ? '#000' : '#F8F9FA', paddingTop: insets.top }]}>
      <StatusBar barStyle={isDark ? 'light-content' : 'dark-content'} />
      <View style={styles.pinContent}>
        <Text style={[styles.pinTitle, { color: colors.textPrimary }]}>
          {step === 'create_pin' ? 'Create PIN' : 'Confirm PIN'}
        </Text>
        <Text style={[styles.pinSubtitle, { color: colors.textSecondary }]}>
          {step === 'create_pin' ? 'Enter a 4-digit PIN' : 'Re-enter your PIN to confirm'}
        </Text>

        {/* PIN Dots */}
        <View style={styles.pinDots}>
          {Array.from({ length: PIN_LENGTH }).map((_, i) => (
            <View
              key={i}
              style={[
                styles.dot,
                {
                  backgroundColor: i < pin.length
                    ? (error ? '#EF4444' : '#10B981')
                    : isDark ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.08)',
                },
              ]}
            />
          ))}
        </View>

        {error ? (
          <Text style={styles.errorText}>{error}</Text>
        ) : (
          <View style={{ height: 24 }} />
        )}

        {/* Dial Pad */}
        <View style={styles.dialPad}>
          {dialPad.map((row, ri) => (
            <View key={ri} style={styles.dialRow}>
              {row.map((key, ki) => {
                if (key === '') return <View key={ki} style={styles.dialBtnEmpty} />;
                if (key === 'del') {
                  return (
                    <TouchableOpacity
                      key={ki}
                      style={[styles.dialBtn, { backgroundColor: isDark ? 'rgba(255,255,255,0.06)' : '#F3F4F6' }]}
                      onPress={handleDelete}
                    >
                      <MaterialCommunityIcons name="backspace-outline" size={24} color={colors.textSecondary} />
                    </TouchableOpacity>
                  );
                }
                return (
                  <TouchableOpacity
                    key={ki}
                    style={[styles.dialBtn, { backgroundColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)' }]}
                    onPress={() => handleDigit(key)}
                    data-testid={`setup-pin-digit-${key}`}
                  >
                    <Text style={[styles.dialText, { color: colors.textPrimary }]}>{key}</Text>
                  </TouchableOpacity>
                );
              })}
            </View>
          ))}
        </View>
      </View>
    </View>
  );
}

export default SecuritySetupScreen;

const styles = StyleSheet.create({
  container: {
    flex: 1,
    position: 'absolute' as any,
    top: 0, left: 0, right: 0, bottom: 0,
    zIndex: 99998,
    ...((Platform.OS === 'web') ? { position: 'fixed' as any, width: '100%', height: '100%' } : {}),
  },
  introContent: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 32,
  },
  introIcon: {
    width: 88,
    height: 88,
    borderRadius: 28,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 24,
  },
  introTitle: {
    fontSize: 26,
    fontFamily: 'DM Sans',
    fontWeight: '700' as any,
    letterSpacing: -0.5,
    marginBottom: 10,
  },
  introSubtitle: {
    fontSize: 15,
    fontFamily: 'DM Sans',
    textAlign: 'center',
    lineHeight: 22,
    marginBottom: 32,
  },
  featureList: { width: '100%', gap: 10, marginBottom: 36 },
  featureRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    padding: 14,
    borderRadius: 14,
  },
  featureIcon: {
    width: 40,
    height: 40,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
  },
  featureText: {
    fontSize: 15,
    fontFamily: 'DM Sans',
    fontWeight: '500' as any,
  },
  setupBtn: { width: '100%', borderRadius: 999, overflow: 'hidden' },
  setupBtnGradient: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    height: 56,
  },
  setupBtnText: {
    color: '#fff',
    fontSize: 17,
    fontFamily: 'DM Sans',
    fontWeight: '700' as any,
  },
  skipBtn: { marginTop: 16, paddingVertical: 12 },
  skipBtnText: { fontSize: 15, fontFamily: 'DM Sans', fontWeight: '500' as any },
  pinContent: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 30,
  },
  pinTitle: {
    fontSize: 24,
    fontFamily: 'DM Sans',
    fontWeight: '700' as any,
    marginBottom: 6,
  },
  pinSubtitle: {
    fontSize: 14,
    fontFamily: 'DM Sans',
    marginBottom: 32,
  },
  pinDots: {
    flexDirection: 'row',
    gap: 16,
    marginBottom: 8,
  },
  dot: { width: 16, height: 16, borderRadius: 8 },
  errorText: {
    color: '#EF4444',
    fontSize: 13,
    fontFamily: 'DM Sans',
    fontWeight: '600' as any,
    height: 24,
    lineHeight: 24,
  },
  dialPad: { marginTop: 20, gap: 12 },
  dialRow: { flexDirection: 'row', gap: 20, justifyContent: 'center' },
  dialBtn: {
    width: DIAL_SIZE,
    height: DIAL_SIZE,
    borderRadius: DIAL_SIZE / 2,
    justifyContent: 'center',
    alignItems: 'center',
  },
  dialBtnEmpty: { width: DIAL_SIZE, height: DIAL_SIZE },
  dialText: { fontSize: 28, fontFamily: 'DM Sans', fontWeight: '600' as any },
});
