import React, { useState, useEffect, useRef } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity, Animated,
  Platform, Dimensions, StatusBar, Vibration,
} from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useSecurity } from '../context/SecurityContext';
import { useTheme } from '../context/ThemeContext';

const { width: SCREEN_WIDTH } = Dimensions.get('window');
const PIN_LENGTH = 4;
const DIAL_SIZE = Math.min(SCREEN_WIDTH * 0.2, 75);

export function LockScreen() {
  const { verifyPin, authenticateWithBiometric, isBiometricEnabled, unlock } = useSecurity();
  const { colors, isDark } = useTheme();
  const insets = useSafeAreaInsets();
  const [pin, setPin] = useState('');
  const [error, setError] = useState('');
  const shakeAnim = useRef(new Animated.Value(0)).current;
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(fadeAnim, { toValue: 1, duration: 400, useNativeDriver: true }).start();
    if (isBiometricEnabled && Platform.OS !== 'web') {
      attemptBiometric();
    }
  }, []);

  const attemptBiometric = async () => {
    const success = await authenticateWithBiometric();
    if (success) unlock();
  };

  const shake = () => {
    if (Platform.OS !== 'web') Vibration.vibrate(200);
    Animated.sequence([
      Animated.timing(shakeAnim, { toValue: 15, duration: 50, useNativeDriver: true }),
      Animated.timing(shakeAnim, { toValue: -15, duration: 50, useNativeDriver: true }),
      Animated.timing(shakeAnim, { toValue: 10, duration: 50, useNativeDriver: true }),
      Animated.timing(shakeAnim, { toValue: -10, duration: 50, useNativeDriver: true }),
      Animated.timing(shakeAnim, { toValue: 0, duration: 50, useNativeDriver: true }),
    ]).start();
  };

  const handleDigit = async (digit: string) => {
    if (pin.length >= PIN_LENGTH) return;
    const newPin = pin + digit;
    setPin(newPin);
    setError('');

    if (newPin.length === PIN_LENGTH) {
      const valid = await verifyPin(newPin);
      if (valid) {
        unlock();
      } else {
        shake();
        setError('Incorrect PIN');
        setTimeout(() => setPin(''), 300);
      }
    }
  };

  const handleDelete = () => {
    setPin(p => p.slice(0, -1));
    setError('');
  };

  const dialPad = [
    ['1', '2', '3'],
    ['4', '5', '6'],
    ['7', '8', '9'],
    [isBiometricEnabled ? 'bio' : '', '0', 'del'],
  ];

  return (
    <View style={[styles.container, { backgroundColor: isDark ? '#000' : '#F8F9FA' }]}>
      <StatusBar barStyle={isDark ? 'light-content' : 'dark-content'} />
      <Animated.View style={[styles.content, { opacity: fadeAnim, paddingTop: insets.top + 40 }]}>
        {/* Logo / Icon */}
        <View style={styles.logoSection}>
          <LinearGradient
            colors={['#10B981', '#059669']}
            style={styles.lockIcon}
          >
            <MaterialCommunityIcons name="shield-lock" size={32} color="#fff" />
          </LinearGradient>
          <Text style={[styles.title, { color: colors.textPrimary }]}>Visor Locked</Text>
          <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
            Enter your PIN to continue
          </Text>
        </View>

        {/* PIN Dots */}
        <Animated.View style={[styles.pinDots, { transform: [{ translateX: shakeAnim }] }]}>
          {Array.from({ length: PIN_LENGTH }).map((_, i) => (
            <View
              key={i}
              style={[
                styles.dot,
                {
                  backgroundColor: i < pin.length
                    ? (error ? '#EF4444' : '#10B981')
                    : isDark ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.08)',
                  transform: [{ scale: i < pin.length ? 1.2 : 1 }],
                },
              ]}
            />
          ))}
        </Animated.View>

        {error ? (
          <Text style={styles.errorText} data-testid="pin-error">{error}</Text>
        ) : (
          <View style={{ height: 24 }} />
        )}

        {/* Dial Pad */}
        <View style={styles.dialPad}>
          {dialPad.map((row, ri) => (
            <View key={ri} style={styles.dialRow}>
              {row.map((key, ki) => {
                if (key === '') return <View key={ki} style={styles.dialBtnEmpty} />;
                if (key === 'bio') {
                  return (
                    <TouchableOpacity
                      key={ki}
                      style={[styles.dialBtn, { backgroundColor: isDark ? 'rgba(255,255,255,0.06)' : '#F3F4F6' }]}
                      onPress={attemptBiometric}
                      data-testid="biometric-btn"
                    >
                      <MaterialCommunityIcons name="fingerprint" size={28} color="#10B981" />
                    </TouchableOpacity>
                  );
                }
                if (key === 'del') {
                  return (
                    <TouchableOpacity
                      key={ki}
                      style={[styles.dialBtn, { backgroundColor: isDark ? 'rgba(255,255,255,0.06)' : '#F3F4F6' }]}
                      onPress={handleDelete}
                      data-testid="pin-delete-btn"
                    >
                      <MaterialCommunityIcons name="backspace-outline" size={24} color={colors.textSecondary} />
                    </TouchableOpacity>
                  );
                }
                return (
                  <TouchableOpacity
                    key={ki}
                    style={[styles.dialBtn, { backgroundColor: isDark ? 'rgba(255,255,255,0.06)' : '#F3F4F6' }]}
                    onPress={() => handleDigit(key)}
                    data-testid={`pin-digit-${key}`}
                  >
                    <Text style={[styles.dialText, { color: colors.textPrimary }]}>{key}</Text>
                  </TouchableOpacity>
                );
              })}
            </View>
          ))}
        </View>
      </Animated.View>
    </View>
  );
}

export default LockScreen;

const styles = StyleSheet.create({
  container: {
    flex: 1,
    position: 'absolute',
    top: 0, left: 0, right: 0, bottom: 0,
    zIndex: 99999,
    ...((Platform.OS === 'web') ? { position: 'fixed' as any, width: '100%', height: '100%' } : {}),
  },
  content: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 30,
  },
  logoSection: {
    alignItems: 'center',
    marginBottom: 40,
  },
  lockIcon: {
    width: 64,
    height: 64,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
  },
  title: {
    fontSize: 24,
    fontFamily: 'DM Sans',
    fontWeight: '700' as any,
    letterSpacing: -0.5,
  },
  subtitle: {
    fontSize: 14,
    fontFamily: 'DM Sans',
    marginTop: 6,
  },
  pinDots: {
    flexDirection: 'row',
    gap: 16,
    marginBottom: 8,
  },
  dot: {
    width: 16,
    height: 16,
    borderRadius: 8,
  },
  errorText: {
    color: '#EF4444',
    fontSize: 13,
    fontFamily: 'DM Sans',
    fontWeight: '600' as any,
    height: 24,
    lineHeight: 24,
  },
  dialPad: {
    marginTop: 20,
    gap: 12,
  },
  dialRow: {
    flexDirection: 'row',
    gap: 20,
    justifyContent: 'center',
  },
  dialBtn: {
    width: DIAL_SIZE,
    height: DIAL_SIZE,
    borderRadius: DIAL_SIZE / 2,
    justifyContent: 'center',
    alignItems: 'center',
  },
  dialBtnEmpty: {
    width: DIAL_SIZE,
    height: DIAL_SIZE,
  },
  dialText: {
    fontSize: 28,
    fontFamily: 'DM Sans',
    fontWeight: '600' as any,
  },
});
