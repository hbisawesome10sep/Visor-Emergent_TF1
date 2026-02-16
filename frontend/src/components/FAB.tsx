import React, { useState } from 'react';
import { 
  View, Text, TouchableOpacity, StyleSheet, 
  Modal, Pressable, Platform 
} from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { BlurView } from 'expo-blur';

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

  const closeMenu = () => setOpen(false);

  const handleAction = (action: Action) => {
    closeMenu();
    setTimeout(() => action.onPress(), 150);
  };

  return (
    <>
      {/* Modal with actions */}
      <Modal
        visible={open}
        transparent
        animationType="fade"
        onRequestClose={closeMenu}
      >
        {/* Backdrop */}
        <Pressable style={styles.backdrop} onPress={closeMenu}>
          <BlurView
            intensity={isDark ? 25 : 35}
            tint={isDark ? 'dark' : 'light'}
            style={StyleSheet.absoluteFill}
          />
          <View style={[styles.overlay, { 
            backgroundColor: isDark ? 'rgba(0,0,0,0.4)' : 'rgba(0,0,0,0.25)' 
          }]} />
        </Pressable>

        {/* Actions menu - positioned at bottom right with safe margins */}
        <View style={styles.menuContainer}>
          {/* Action buttons - stacked vertically */}
          {actions.map((action, index) => (
            <TouchableOpacity
              key={action.label}
              style={styles.actionItem}
              onPress={() => handleAction(action)}
              activeOpacity={0.9}
            >
              <View style={[styles.labelBox, {
                backgroundColor: isDark ? 'rgba(10,10,11,0.95)' : 'rgba(255,255,255,0.95)',
                borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
              }]}>
                <Text style={[styles.labelText, { color: colors.textPrimary }]}>
                  {action.label}
                </Text>
              </View>
              <View style={[styles.iconBtn, { backgroundColor: action.color }]}>
                <MaterialCommunityIcons name={action.icon} size={20} color="#fff" />
              </View>
            </TouchableOpacity>
          ))}

          {/* Close button */}
          <TouchableOpacity
            style={[styles.mainFab, { backgroundColor: colors.primary }]}
            onPress={closeMenu}
            activeOpacity={0.9}
          >
            <MaterialCommunityIcons name="close" size={24} color="#fff" />
          </TouchableOpacity>
        </View>
      </Modal>

      {/* Main FAB - visible when menu is closed */}
      {!open && (
        <TouchableOpacity
          style={[styles.fabButton, { backgroundColor: colors.primary }]}
          onPress={() => setOpen(true)}
          activeOpacity={0.9}
        >
          <MaterialCommunityIcons name="plus" size={26} color="#fff" />
        </TouchableOpacity>
      )}
    </>
  );
}

const styles = StyleSheet.create({
  // Main FAB button when closed
  fabButton: {
    position: 'absolute',
    right: 20,
    bottom: Platform.OS === 'ios' ? 100 : 85,
    width: 56,
    height: 56,
    borderRadius: 28,
    justifyContent: 'center',
    alignItems: 'center',
    elevation: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 6,
    zIndex: 999,
  },

  // Modal backdrop
  backdrop: {
    flex: 1,
  },
  overlay: {
    ...StyleSheet.absoluteFillObject,
  },

  // Menu container - fixed position from bottom-right
  menuContainer: {
    position: 'absolute',
    right: 20,
    bottom: Platform.OS === 'ios' ? 100 : 85,
    alignItems: 'flex-end',
  },

  // Each action item row
  actionItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 14,
  },

  // Label box
  labelBox: {
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 12,
    borderWidth: 1,
    marginRight: 12,
    elevation: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.15,
    shadowRadius: 4,
  },
  labelText: {
    fontSize: 14,
    fontFamily: 'DM Sans', fontWeight: '600' as any,
  },

  // Icon button
  iconBtn: {
    width: 44,
    height: 44,
    borderRadius: 22,
    justifyContent: 'center',
    alignItems: 'center',
    elevation: 5,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 4,
  },

  // Main FAB in modal (close button)
  mainFab: {
    width: 56,
    height: 56,
    borderRadius: 28,
    justifyContent: 'center',
    alignItems: 'center',
    elevation: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 6,
  },
});
