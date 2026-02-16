import React, { useState, useRef } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Animated, Dimensions, Platform } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { BlurView } from 'expo-blur';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

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
  const backdropAnim = useRef(new Animated.Value(0)).current;

  const toggle = () => {
    const toOpen = !open;
    setOpen(toOpen);
    Animated.parallel([
      Animated.spring(rotateAnim, { toValue: toOpen ? 1 : 0, useNativeDriver: true, friction: 6 }),
      Animated.spring(scaleAnim, { toValue: toOpen ? 1 : 0, useNativeDriver: true, friction: 6 }),
      Animated.timing(backdropAnim, { toValue: toOpen ? 1 : 0, duration: 200, useNativeDriver: true }),
    ]).start();
  };

  const rotation = rotateAnim.interpolate({
    inputRange: [0, 1],
    outputRange: ['0deg', '45deg'],
  });

  return (
    <>
      {/* Full screen translucent backdrop */}
      {open && (
        <TouchableOpacity
          activeOpacity={1}
          onPress={toggle}
          style={styles.fullBackdrop}
        >
          <Animated.View style={[styles.backdropFill, { opacity: backdropAnim }]}>
            <BlurView
              intensity={isDark ? 40 : 50}
              tint={isDark ? 'dark' : 'light'}
              style={StyleSheet.absoluteFill}
            />
            <View style={[styles.backdropOverlay, { backgroundColor: isDark ? 'rgba(0,0,0,0.4)' : 'rgba(255,255,255,0.4)' }]} />
          </Animated.View>
        </TouchableOpacity>
      )}

      <View style={styles.container} pointerEvents="box-none">
        {/* Action items */}
        {actions.map((action, index) => {
          const translateY = scaleAnim.interpolate({
            inputRange: [0, 1],
            outputRange: [0, -(70 * (index + 1))],
          });
          const opacity = scaleAnim.interpolate({
            inputRange: [0, 0.5, 1],
            outputRange: [0, 0, 1],
          });
          const scale = scaleAnim.interpolate({
            inputRange: [0, 1],
            outputRange: [0.8, 1],
          });

          return (
            <Animated.View
              key={action.label}
              style={[styles.actionRow, { transform: [{ translateY }, { scale }], opacity }]}
            >
              <View style={[styles.actionLabel, {
                backgroundColor: isDark ? 'rgba(30, 41, 59, 0.98)' : 'rgba(255, 255, 255, 0.98)',
                borderColor: isDark ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.1)',
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
        <TouchableOpacity 
          testID="fab-main-btn" 
          style={[styles.mainBtn, { backgroundColor: colors.primary }]} 
          onPress={toggle} 
          activeOpacity={0.8}
        >
          <Animated.View style={{ transform: [{ rotate: rotation }] }}>
            <MaterialCommunityIcons name="plus" size={28} color="#fff" />
          </Animated.View>
        </TouchableOpacity>
      </View>
    </>
  );
}

const styles = StyleSheet.create({
  fullBackdrop: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    zIndex: 99,
  },
  backdropFill: {
    flex: 1,
  },
  backdropOverlay: {
    ...StyleSheet.absoluteFillObject,
  },
  container: {
    position: 'absolute',
    right: 20,
    bottom: Platform.OS === 'ios' ? 100 : 90,
    alignItems: 'flex-end',
    zIndex: 100,
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
    gap: 12,
  },
  actionLabel: {
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 14,
    borderWidth: 1,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 8,
    elevation: 4,
  },
  actionLabelText: {
    fontSize: 14,
    fontWeight: '600',
  },
  actionBtn: {
    width: 52,
    height: 52,
    borderRadius: 26,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.25,
    shadowRadius: 6,
    elevation: 5,
  },
});
