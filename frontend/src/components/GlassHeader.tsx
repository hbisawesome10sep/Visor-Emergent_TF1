import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Platform } from 'react-native';
import { BlurView } from 'expo-blur';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';

type FrequencyOption = 'Quarter' | 'Month' | 'Year';

type Props = {
  greeting: string;
  userName: string;
  monthYear: string;
  selectedFrequency: FrequencyOption;
  onFrequencyChange: (freq: FrequencyOption) => void;
  isDark: boolean;
  onThemeToggle: () => void;
  colors: any;
};

export default function GlassHeader({
  greeting,
  userName,
  monthYear,
  selectedFrequency,
  onFrequencyChange,
  isDark,
  onThemeToggle,
  colors,
}: Props) {
  const frequencies: FrequencyOption[] = ['Quarter', 'Month', 'Year'];

  return (
    <View style={styles.container}>
      <BlurView
        intensity={isDark ? 60 : 80}
        tint={isDark ? 'dark' : 'light'}
        style={[
          styles.blurContainer,
          {
            backgroundColor: isDark ? 'rgba(30, 41, 59, 0.7)' : 'rgba(255, 255, 255, 0.7)',
            borderBottomColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)',
          },
        ]}
      >
        <View style={styles.content}>
          <View style={styles.leftSection}>
            <View style={styles.greetingRow}>
              <LinearGradient
                colors={['#3B82F6', '#6366F1']}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 0 }}
                style={styles.gradientText}
              >
                <Text style={styles.greeting}>{greeting}, </Text>
              </LinearGradient>
              <Text style={[styles.userName, { color: colors.textPrimary }]}>{userName}</Text>
            </View>
            <Text style={[styles.monthYear, { color: colors.textSecondary }]}>{monthYear}</Text>
          </View>

          <View style={styles.rightSection}>
            {/* Frequency Selector Pills */}
            <View
              style={[
                styles.frequencyContainer,
                {
                  backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
                },
              ]}
            >
              {frequencies.map((freq) => (
                <TouchableOpacity
                  key={freq}
                  style={[
                    styles.frequencyPill,
                    selectedFrequency === freq && {
                      backgroundColor: colors.primary,
                    },
                  ]}
                  onPress={() => onFrequencyChange(freq)}
                >
                  <Text
                    style={[
                      styles.frequencyText,
                      {
                        color:
                          selectedFrequency === freq ? '#fff' : colors.textSecondary,
                      },
                    ]}
                  >
                    {freq.charAt(0)}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            {/* Theme Toggle */}
            <TouchableOpacity
              style={[
                styles.themeToggle,
                {
                  backgroundColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.06)',
                },
              ]}
              onPress={onThemeToggle}
            >
              <MaterialCommunityIcons
                name={isDark ? 'weather-sunny' : 'weather-night'}
                size={18}
                color={isDark ? '#FBBF24' : '#6366F1'}
              />
            </TouchableOpacity>
          </View>
        </View>
      </BlurView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    zIndex: 100,
  },
  blurContainer: {
    paddingTop: Platform.OS === 'ios' ? 50 : 10,
    paddingHorizontal: 16,
    paddingBottom: 12,
    borderBottomWidth: 1,
  },
  content: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  leftSection: {
    flex: 1,
  },
  greetingRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  gradientText: {
    borderRadius: 4,
    overflow: 'hidden',
  },
  greeting: {
    fontSize: 18,
    fontFamily: 'SpaceGrotesk_700Bold',
    color: '#fff',
    paddingHorizontal: 2,
  },
  userName: {
    fontSize: 18,
    fontFamily: 'SpaceGrotesk_700Bold',
  },
  monthYear: {
    fontSize: 13,
    fontFamily: 'Outfit_500Medium',
    marginTop: 2,
  },
  rightSection: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  frequencyContainer: {
    flexDirection: 'row',
    borderRadius: 10,
    padding: 3,
  },
  frequencyPill: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
  },
  frequencyText: {
    fontSize: 12,
    fontFamily: 'SpaceGrotesk_700Bold',
  },
  themeToggle: {
    width: 36,
    height: 36,
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
  },
});
