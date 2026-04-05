// /app/frontend/src/components/experience/ModeNudge.tsx
/**
 * Mode Nudge Component
 * Shows AI-powered suggestions to upgrade experience mode
 */

import React from 'react';
import { 
  View, 
  Text, 
  TouchableOpacity, 
  StyleSheet, 
  Modal,
  Animated
} from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useExperienceMode } from '../../context/ExperienceModeContext';
import { useTheme } from '../../context/ThemeContext';

export function ModeNudge() {
  const { pendingNudge, respondToNudge, dismissNudge } = useExperienceMode();
  const { colors, isDark } = useTheme();
  
  if (!pendingNudge) return null;
  
  const { message, cta, mode_info, suggested_mode } = pendingNudge;
  const modeColor = mode_info?.color || '#6366F1';
  const modeIcon = mode_info?.icon || 'chart-line';
  
  const handleAccept = () => {
    respondToNudge(true);
  };
  
  const handleDismiss = () => {
    respondToNudge(false);
    dismissNudge();
  };
  
  return (
    <Modal
      visible={true}
      animationType="fade"
      transparent
      onRequestClose={handleDismiss}
    >
      <View style={styles.overlay}>
        <View style={[styles.container, { backgroundColor: isDark ? '#1a1a2e' : '#fff' }]}>
          {/* Close button */}
          <TouchableOpacity style={styles.closeButton} onPress={handleDismiss}>
            <MaterialCommunityIcons name="close" size={24} color={colors.textSecondary} />
          </TouchableOpacity>
          
          {/* Icon */}
          <View style={[styles.iconContainer, { backgroundColor: `${modeColor}20` }]}>
            <MaterialCommunityIcons name="robot" size={32} color={modeColor} />
          </View>
          
          {/* Message */}
          <Text style={[styles.title, { color: colors.textPrimary }]}>
            Visor AI Suggestion
          </Text>
          <Text style={[styles.message, { color: colors.textSecondary }]}>
            {message}
          </Text>
          
          {/* Mode preview */}
          <View style={[styles.modePreview, { borderColor: modeColor }]}>
            <View style={[styles.modeIconSmall, { backgroundColor: `${modeColor}20` }]}>
              <MaterialCommunityIcons name={modeIcon as any} size={20} color={modeColor} />
            </View>
            <View>
              <Text style={[styles.modeName, { color: colors.textPrimary }]}>
                {mode_info?.title || suggested_mode} Mode
              </Text>
              <Text style={[styles.modeSubtitle, { color: modeColor }]}>
                {mode_info?.subtitle}
              </Text>
            </View>
          </View>
          
          {/* Actions */}
          <View style={styles.actions}>
            <TouchableOpacity
              style={[styles.acceptButton, { backgroundColor: modeColor }]}
              onPress={handleAccept}
            >
              <Text style={styles.acceptButtonText}>{cta || 'Upgrade'}</Text>
              <MaterialCommunityIcons name="arrow-right" size={18} color="#fff" />
            </TouchableOpacity>
            
            <TouchableOpacity style={styles.dismissButton} onPress={handleDismiss}>
              <Text style={[styles.dismissText, { color: colors.textSecondary }]}>
                Maybe later
              </Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.7)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  container: {
    width: '100%',
    maxWidth: 340,
    borderRadius: 24,
    padding: 24,
    alignItems: 'center',
  },
  closeButton: {
    position: 'absolute',
    top: 16,
    right: 16,
    padding: 4,
  },
  iconContainer: {
    width: 64,
    height: 64,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
    marginTop: 8,
  },
  title: {
    fontSize: 20,
    fontWeight: '700',
    marginBottom: 12,
    textAlign: 'center',
  },
  message: {
    fontSize: 15,
    lineHeight: 22,
    textAlign: 'center',
    marginBottom: 20,
  },
  modePreview: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    padding: 14,
    borderRadius: 12,
    borderWidth: 2,
    width: '100%',
    marginBottom: 24,
  },
  modeIconSmall: {
    width: 40,
    height: 40,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  modeName: {
    fontSize: 16,
    fontWeight: '600',
  },
  modeSubtitle: {
    fontSize: 13,
    marginTop: 2,
  },
  actions: {
    width: '100%',
    gap: 12,
  },
  acceptButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    padding: 16,
    borderRadius: 14,
  },
  acceptButtonText: {
    color: '#fff',
    fontWeight: '700',
    fontSize: 16,
  },
  dismissButton: {
    alignItems: 'center',
    padding: 12,
  },
  dismissText: {
    fontSize: 14,
  },
});

export default ModeNudge;
