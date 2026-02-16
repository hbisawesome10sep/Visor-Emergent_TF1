import React, { useEffect, useRef } from 'react';
import { View, Text, StyleSheet, Animated, TouchableOpacity, Dimensions } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';

const { width: SCREEN_WIDTH } = Dimensions.get('window');
const CARD_WIDTH = (SCREEN_WIDTH - 52) / 3;

type Props = {
  title: string;
  amount: string;
  percentChange?: number;
  fillPercent: number;
  gradient: [string, string];
  icon: any;
  onPress?: () => void;
  colors: any;
  isDark: boolean;
};

export default function LiquidFillCard({
  title, amount, percentChange, fillPercent, gradient, icon, onPress, colors, isDark,
}: Props) {
  const fillAnim = useRef(new Animated.Value(0)).current;
  const waveAnim = useRef(new Animated.Value(0)).current;
  const bubbleAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(fillAnim, {
      toValue: Math.min(Math.max(fillPercent, 0), 100),
      duration: 1500,
      useNativeDriver: false,
    }).start();

    Animated.loop(
      Animated.sequence([
        Animated.timing(waveAnim, { toValue: 1, duration: 3000, useNativeDriver: true }),
        Animated.timing(waveAnim, { toValue: 0, duration: 3000, useNativeDriver: true }),
      ])
    ).start();

    Animated.loop(
      Animated.sequence([
        Animated.timing(bubbleAnim, { toValue: 1, duration: 2000, useNativeDriver: true }),
        Animated.timing(bubbleAnim, { toValue: 0, duration: 0, useNativeDriver: true }),
      ])
    ).start();
  }, [fillPercent]);

  const fillHeight = fillAnim.interpolate({
    inputRange: [0, 100],
    outputRange: ['0%', '100%'],
  });

  const waveTranslateX = waveAnim.interpolate({
    inputRange: [0, 1],
    outputRange: [-20, 20],
  });

  const bubbleTranslateY = bubbleAnim.interpolate({
    inputRange: [0, 1],
    outputRange: [0, -60],
  });

  const bubbleOpacity = bubbleAnim.interpolate({
    inputRange: [0, 0.7, 1],
    outputRange: [0.6, 0.3, 0],
  });

  // Neon glow color derived from first gradient color
  const glowColor = gradient[0];

  return (
    <TouchableOpacity
      style={[
        styles.card,
        {
          shadowColor: isDark ? glowColor : '#000',
          shadowOpacity: isDark ? 0.5 : 0.15,
          shadowRadius: isDark ? 16 : 10,
          borderColor: isDark ? `${glowColor}30` : 'rgba(0,0,0,0.06)',
        },
      ]}
      onPress={onPress}
      activeOpacity={0.95}
      disabled={!onPress}
    >
      <LinearGradient
        colors={gradient}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={styles.gradient}
      >
        {/* Liquid fill animation */}
        <View style={styles.liquidContainer}>
          <Animated.View
            style={[styles.liquidFill, { height: fillHeight, backgroundColor: 'rgba(255, 255, 255, 0.12)' }]}
          >
            <Animated.View style={[styles.wave, { transform: [{ translateX: waveTranslateX }] }]} />
          </Animated.View>
          <Animated.View
            style={[styles.bubble, { transform: [{ translateY: bubbleTranslateY }], opacity: bubbleOpacity }]}
          />
          <Animated.View
            style={[styles.bubble, styles.bubble2, { transform: [{ translateY: bubbleTranslateY }], opacity: bubbleOpacity }]}
          />
        </View>

        {/* Content */}
        <View style={styles.content}>
          <View style={styles.iconContainer}>
            <MaterialCommunityIcons name={icon} size={18} color="rgba(255,255,255,0.95)" />
          </View>
          <Text style={styles.title}>{title}</Text>
          <Text style={styles.amount}>{amount}</Text>
          {percentChange !== undefined && (
            <View style={styles.changeRow}>
              <MaterialCommunityIcons
                name={percentChange >= 0 ? 'trending-up' : 'trending-down'}
                size={14}
                color="rgba(255,255,255,0.9)"
              />
              <Text style={styles.changeText}>
                {Math.abs(percentChange).toFixed(1)}%
              </Text>
            </View>
          )}
        </View>
      </LinearGradient>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: {
    flex: 1,
    minWidth: CARD_WIDTH,
    height: 140,
    borderRadius: 20,
    overflow: 'hidden',
    shadowOffset: { width: 0, height: 4 },
    elevation: 10,
    borderWidth: 1,
  },
  gradient: {
    flex: 1,
    position: 'relative',
  },
  liquidContainer: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'flex-end',
    overflow: 'hidden',
  },
  liquidFill: {
    width: '100%',
    position: 'relative',
    overflow: 'hidden',
  },
  wave: {
    position: 'absolute',
    top: -8,
    left: -20,
    right: -20,
    height: 16,
    backgroundColor: 'rgba(255,255,255,0.08)',
    borderRadius: 8,
  },
  bubble: {
    position: 'absolute',
    bottom: 20,
    left: '30%',
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: 'rgba(255,255,255,0.4)',
  },
  bubble2: {
    left: '60%',
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  content: {
    flex: 1,
    padding: 14,
    justifyContent: 'space-between',
    zIndex: 2,
  },
  iconContainer: {
    width: 34,
    height: 34,
    borderRadius: 10,
    backgroundColor: 'rgba(0,0,0,0.15)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  title: {
    fontFamily: 'DM Sans', fontWeight: '600' as any,
    fontSize: 11,
    color: 'rgba(255,255,255,0.85)',
    textTransform: 'uppercase',
    letterSpacing: 0.8,
  },
  amount: {
    fontFamily: 'DM Sans', fontWeight: '700' as any,
    fontSize: 20,
    color: '#fff',
    letterSpacing: -0.5,
  },
  changeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 3,
  },
  changeText: {
    fontFamily: 'DM Sans', fontWeight: '600' as any,
    fontSize: 12,
    color: 'rgba(255,255,255,0.9)',
  },
});
