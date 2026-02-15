import React, { useState, useRef } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Animated } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';

type Action = {
  icon: any;
  label: string;
  color: string;
  onPress: () => void;
};

type Props = {
  actions: Action[];
  colors: any;
  isDark: boolean;
};

export default function FAB({ actions, colors, isDark }: Props) {
  const [open, setOpen] = useState(false);
  const rotateAnim = useRef(new Animated.Value(0)).current;
  const scaleAnim = useRef(new Animated.Value(0)).current;

  const toggle = () => {
    const toOpen = !open;
    setOpen(toOpen);
    Animated.parallel([
      Animated.spring(rotateAnim, { toValue: toOpen ? 1 : 0, useNativeDriver: true, friction: 6 }),
      Animated.spring(scaleAnim, { toValue: toOpen ? 1 : 0, useNativeDriver: true, friction: 6 }),
    ]).start();
  };

  const rotation = rotateAnim.interpolate({
    inputRange: [0, 1],
    outputRange: ['0deg', '45deg'],
  });

  return (
    <View style={styles.container} pointerEvents="box-none">
      {/* Backdrop */}
      {open && (
        <TouchableOpacity
          testID="fab-backdrop"
          style={styles.backdrop}
          activeOpacity={1}
          onPress={toggle}
        />
      )}

      {/* Action items */}
      {actions.map((action, index) => {
        const translateY = scaleAnim.interpolate({
          inputRange: [0, 1],
          outputRange: [0, -(60 * (index + 1))],
        });
        const opacity = scaleAnim.interpolate({
          inputRange: [0, 0.5, 1],
          outputRange: [0, 0, 1],
        });

        return (
          <Animated.View
            key={action.label}
            style={[styles.actionRow, { transform: [{ translateY }], opacity }]}
          >
            <View style={[styles.actionLabel, {
              backgroundColor: isDark ? 'rgba(30, 41, 59, 0.95)' : 'rgba(255, 255, 255, 0.95)',
              borderColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)',
            }]}>
              <Text style={[styles.actionLabelText, { color: colors.textPrimary }]}>{action.label}</Text>
            </View>
            <TouchableOpacity
              testID={`fab-action-${action.label.toLowerCase().replace(/\s/g, '-')}`}
              style={[styles.actionBtn, { backgroundColor: action.color }]}
              onPress={() => { toggle(); action.onPress(); }}
            >
              <MaterialCommunityIcons name={action.icon} size={22} color="#fff" />
            </TouchableOpacity>
          </Animated.View>
        );
      })}

      {/* Main FAB */}
      <TouchableOpacity testID="fab-main-btn" style={[styles.mainBtn, { backgroundColor: colors.primary }]} onPress={toggle} activeOpacity={0.8}>
        <Animated.View style={{ transform: [{ rotate: rotation }] }}>
          <MaterialCommunityIcons name="plus" size={28} color="#fff" />
        </Animated.View>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    right: 20,
    bottom: 24,
    alignItems: 'flex-end',
    zIndex: 100,
  },
  backdrop: {
    ...StyleSheet.absoluteFillObject,
    left: -1000,
    top: -1000,
    right: -1000,
    bottom: -1000,
  },
  mainBtn: {
    width: 60,
    height: 60,
    borderRadius: 30,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
  },
  actionRow: {
    position: 'absolute',
    bottom: 0,
    right: 0,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  actionLabel: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 10,
    borderWidth: 1,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  actionLabelText: {
    fontSize: 13,
    fontWeight: '600',
  },
  actionBtn: {
    width: 48,
    height: 48,
    borderRadius: 24,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
    elevation: 4,
  },
});
