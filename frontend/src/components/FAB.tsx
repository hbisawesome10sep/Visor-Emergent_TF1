import React, { useState, useRef } from 'react';
import { 
  View, Text, TouchableOpacity, StyleSheet, Animated, 
  Dimensions, Modal, Pressable, Platform 
} from 'react-native';
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

  const toggle = () => {
    const toOpen = !open;
    setOpen(toOpen);
    Animated.parallel([
      Animated.spring(rotateAnim, { toValue: toOpen ? 1 : 0, useNativeDriver: true, friction: 6 }),
      Animated.spring(scaleAnim, { toValue: toOpen ? 1 : 0, useNativeDriver: true, friction: 6 }),
    ]).start();
  };

  const closeMenu = () => {
    setOpen(false);
    Animated.parallel([
      Animated.spring(rotateAnim, { toValue: 0, useNativeDriver: true, friction: 6 }),
      Animated.spring(scaleAnim, { toValue: 0, useNativeDriver: true, friction: 6 }),
    ]).start();
  };

  const handleAction = (action: Action) => {
    closeMenu();
    setTimeout(() => action.onPress(), 100);
  };

  const rotation = rotateAnim.interpolate({
    inputRange: [0, 1],
    outputRange: ['0deg', '45deg'],
  });

  return (
    <>
      {/* Full-screen modal backdrop */}
      <Modal
        visible={open}
        transparent
        animationType="fade"
        onRequestClose={closeMenu}
      >
        <Pressable style={styles.modalBackdrop} onPress={closeMenu}>
          <BlurView
            intensity={isDark ? 30 : 40}
            tint={isDark ? 'dark' : 'light'}
            style={StyleSheet.absoluteFill}
          />
          <View style={[styles.backdropOverlay, { 
            backgroundColor: isDark ? 'rgba(0,0,0,0.5)' : 'rgba(0,0,0,0.3)' 
          }]} />
        </Pressable>

        {/* Actions Container - positioned from bottom, centered with padding */}
        <View style={styles.actionsWrapper} pointerEvents="box-none">
          <View style={styles.actionsContainer}>
            {actions.map((action, index) => {
              const translateY = scaleAnim.interpolate({
                inputRange: [0, 1],
                outputRange: [0, -(60 * (index + 1))],
              });
              const opacity = scaleAnim.interpolate({
                inputRange: [0, 0.3, 1],
                outputRange: [0, 0, 1],
              });
              const scale = scaleAnim.interpolate({
                inputRange: [0, 1],
                outputRange: [0.6, 1],
              });

              return (
                <Animated.View
                  key={action.label}
                  style={[
                    styles.actionRow,
                    { 
                      transform: [{ translateY }, { scale }], 
                      opacity,
                    }
                  ]}
                >
                  <TouchableOpacity
                    style={[styles.actionLabel, {
                      backgroundColor: isDark ? 'rgba(30, 41, 59, 0.98)' : 'rgba(255, 255, 255, 0.98)',
                      borderColor: isDark ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.1)',
                    }]}
                    onPress={() => handleAction(action)}
                    activeOpacity={0.8}
                  >
                    <Text style={[styles.actionLabelText, { color: colors.textPrimary }]}>
                      {action.label}
                    </Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={[styles.actionBtn, { backgroundColor: action.color }]}
                    onPress={() => handleAction(action)}
                    activeOpacity={0.8}
                  >
                    <MaterialCommunityIcons name={action.icon} size={20} color="#fff" />
                  </TouchableOpacity>
                </Animated.View>
              );
            })}

            {/* Close FAB button inside modal */}
            <TouchableOpacity
              style={[styles.mainBtn, { backgroundColor: colors.primary }]}
              onPress={closeMenu}
              activeOpacity={0.8}
            >
              <Animated.View style={{ transform: [{ rotate: rotation }] }}>
                <MaterialCommunityIcons name="plus" size={26} color="#fff" />
              </Animated.View>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

      {/* Main FAB button - always visible */}
      {!open && (
        <View style={styles.fabContainer}>
          <TouchableOpacity
            testID="fab-main-btn"
            style={[styles.mainBtn, { backgroundColor: colors.primary }]}
            onPress={toggle}
            activeOpacity={0.8}
          >
            <MaterialCommunityIcons name="plus" size={26} color="#fff" />
          </TouchableOpacity>
        </View>
      )}
    </>
  );
}

const styles = StyleSheet.create({
  fabContainer: {
    position: 'absolute',
    right: 24,
    bottom: Platform.OS === 'ios' ? 100 : 90,
    zIndex: 100,
  },
  modalBackdrop: {
    flex: 1,
  },
  backdropOverlay: {
    ...StyleSheet.absoluteFillObject,
  },
  actionsWrapper: {
    position: 'absolute',
    bottom: Platform.OS === 'ios' ? 100 : 90,
    left: 0,
    right: 0,
    alignItems: 'flex-end',
    paddingRight: 24,
  },
  actionsContainer: {
    alignItems: 'flex-end',
  },
  mainBtn: {
    width: 56,
    height: 56,
    borderRadius: 28,
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
    paddingVertical: 12,
    borderRadius: 14,
    borderWidth: 1,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.15,
    shadowRadius: 6,
    elevation: 4,
  },
  actionLabelText: {
    fontSize: 15,
    fontWeight: '600',
  },
  actionBtn: {
    width: 44,
    height: 44,
    borderRadius: 22,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 4,
    elevation: 5,
  },
});
