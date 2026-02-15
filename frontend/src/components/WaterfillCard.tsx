import React, { useEffect, useRef } from 'react';
import { View, Text, StyleSheet, Animated } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';

type Props = {
  title: string;
  amount: string;
  subtitle: string;
  fillPercent: number; // 0-100
  icon: any;
  mode: 'drain' | 'fill'; // drain = starts full, fill = starts empty
  colors: any;
  isDark: boolean;
  accentColor: string;
  iconBgColor: string;
};

function getSemanticColor(percent: number, mode: 'drain' | 'fill'): string {
  // For drain: high % = good (green), low % = bad (red)
  // For fill: low % = good (green), high % = bad (red)
  const effectivePercent = mode === 'drain' ? percent : percent;
  const thresholds = mode === 'drain'
    ? { green: 50, yellow: 25, orange: 10 }
    : { green: 50, yellow: 75, orange: 90 };

  if (mode === 'drain') {
    if (effectivePercent > 50) return '#10B981';
    if (effectivePercent > 25) return '#F59E0B';
    if (effectivePercent > 10) return '#F97316';
    return '#EF4444';
  } else {
    if (effectivePercent < 50) return '#10B981';
    if (effectivePercent < 75) return '#F59E0B';
    if (effectivePercent < 90) return '#F97316';
    return '#EF4444';
  }
}

export default function WaterfillCard({ title, amount, subtitle, fillPercent, icon, mode, colors, isDark, accentColor, iconBgColor }: Props) {
  const animatedFill = useRef(new Animated.Value(0)).current;
  const waveAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(animatedFill, {
      toValue: Math.min(Math.max(fillPercent, 0), 100),
      duration: 1200,
      useNativeDriver: false,
    }).start();

    // Wave animation loop
    Animated.loop(
      Animated.sequence([
        Animated.timing(waveAnim, { toValue: 1, duration: 2000, useNativeDriver: true }),
        Animated.timing(waveAnim, { toValue: 0, duration: 2000, useNativeDriver: true }),
      ])
    ).start();
  }, [fillPercent]);

  const semanticColor = getSemanticColor(fillPercent, mode);
  const fillHeight = animatedFill.interpolate({
    inputRange: [0, 100],
    outputRange: ['0%', '100%'],
  });

  const waveTranslateX = waveAnim.interpolate({
    inputRange: [0, 1],
    outputRange: [-8, 8],
  });

  return (
    <View style={[styles.card, {
      backgroundColor: isDark ? 'rgba(30, 41, 59, 0.8)' : 'rgba(255, 255, 255, 0.85)',
      borderColor: isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(255, 255, 255, 0.6)',
      shadowColor: isDark ? '#000' : '#64748B',
    }]}>
      {/* Waterfill Background */}
      <View style={styles.fillContainer}>
        <Animated.View style={[styles.fillLevel, {
          height: fillHeight,
          backgroundColor: `${semanticColor}15`,
        }]}>
          {/* Wave top edge */}
          <Animated.View style={[styles.waveEdge, {
            backgroundColor: `${semanticColor}20`,
            transform: [{ translateX: waveTranslateX }],
          }]} />
        </Animated.View>
      </View>

      {/* Content */}
      <View style={styles.content}>
        <View style={styles.topRow}>
          <View style={[styles.iconBubble, { backgroundColor: iconBgColor }]}>
            <MaterialCommunityIcons name={icon} size={18} color={accentColor} />
          </View>
          <View style={[styles.percentBadge, { backgroundColor: `${semanticColor}20` }]}>
            <Text style={[styles.percentText, { color: semanticColor }]}>
              {fillPercent.toFixed(0)}%
            </Text>
          </View>
        </View>

        <Text style={[styles.amount, { color: colors.textPrimary }]}>{amount}</Text>
        <Text style={[styles.title, { color: colors.textSecondary }]}>{title}</Text>

        {/* Mini fill bar */}
        <View style={[styles.miniBar, { backgroundColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)' }]}>
          <Animated.View style={[styles.miniBarFill, {
            width: fillHeight,
            backgroundColor: semanticColor,
          }]} />
        </View>
        <Text style={[styles.subtitle, { color: colors.textSecondary }]}>{subtitle}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    flex: 1,
    minWidth: 155,
    borderRadius: 20,
    borderWidth: 1,
    overflow: 'hidden',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.12,
    shadowRadius: 16,
    elevation: 6,
  },
  fillContainer: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'flex-end',
  },
  fillLevel: {
    width: '100%',
    borderTopLeftRadius: 12,
    borderTopRightRadius: 12,
    overflow: 'hidden',
  },
  waveEdge: {
    height: 6,
    borderRadius: 3,
    marginHorizontal: -4,
  },
  content: {
    padding: 16,
    zIndex: 1,
  },
  topRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 14,
  },
  iconBubble: {
    width: 36,
    height: 36,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
  },
  percentBadge: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 8,
  },
  percentText: {
    fontSize: 12,
    fontWeight: '700',
  },
  amount: {
    fontSize: 20,
    fontWeight: '800',
    letterSpacing: -0.5,
  },
  title: {
    fontSize: 12,
    fontWeight: '500',
    marginTop: 2,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  miniBar: {
    height: 4,
    borderRadius: 2,
    marginTop: 12,
    overflow: 'hidden',
  },
  miniBarFill: {
    height: '100%',
    borderRadius: 2,
  },
  subtitle: {
    fontSize: 11,
    marginTop: 4,
  },
});
