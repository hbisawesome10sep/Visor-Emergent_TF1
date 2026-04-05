// /app/frontend/src/components/experience/ModeSelector.tsx
/**
 * Mode Selector Component
 * Allows users to choose their experience mode
 */

import React, { useState, useEffect } from 'react';
import { 
  View, 
  Text, 
  TouchableOpacity, 
  StyleSheet, 
  Modal, 
  ScrollView,
  Dimensions,
  ActivityIndicator
} from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useExperienceMode, ExperienceMode } from '../../context/ExperienceModeContext';
import { useTheme } from '../../context/ThemeContext';

const { height: SCREEN_HEIGHT } = Dimensions.get('window');

interface ModeConfig {
  title: string;
  subtitle: string;
  description: string;
  icon: string;
  color: string;
  features: string[];
}

const MODE_CONFIG: Record<ExperienceMode, ModeConfig> = {
  essential: {
    title: 'Essential',
    subtitle: 'Just keep it simple',
    description: 'AI does the heavy lifting. See only what matters.',
    icon: 'leaf',
    color: '#10B981',
    features: ['AI chat as home', 'Monthly snapshot', 'Smart alerts', 'Auto bank import'],
  },
  plus: {
    title: 'Plus',
    subtitle: 'I want more visibility',
    description: 'Full control with guidance. Explore and plan.',
    icon: 'chart-line',
    color: '#6366F1',
    features: ['Everything in Essential', 'Full transactions', 'Holdings & SIP', 'Health score', 'Tax basics'],
  },
  full: {
    title: 'Full',
    subtitle: 'Give me everything',
    description: 'Complete platform access for power users.',
    icon: 'rocket-launch',
    color: '#F59E0B',
    features: ['Everything in Plus', 'Bookkeeping', 'Full tax module', 'Portfolio analytics', 'All exports'],
  },
};

interface ModeSelectorProps {
  visible: boolean;
  onClose: () => void;
  isOnboarding?: boolean;
}

export function ModeSelector({ visible, onClose, isOnboarding = false }: ModeSelectorProps) {
  const { mode, setMode, completeOnboarding } = useExperienceMode();
  const { colors, isDark } = useTheme();
  const [selectedMode, setSelectedMode] = useState<ExperienceMode>(mode);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setSelectedMode(mode);
  }, [mode, visible]);

  const handleSelectMode = async (newMode: ExperienceMode) => {
    setSelectedMode(newMode);
  };

  const handleConfirm = async () => {
    setSaving(true);
    try {
      await setMode(selectedMode, isOnboarding ? 'onboarding' : 'manual');
      if (isOnboarding) {
        await completeOnboarding();
      }
      onClose();
    } catch (e) {
      console.error('Failed to set mode:', e);
    } finally {
      setSaving(false);
    }
  };

  const handleLetAIDecide = async () => {
    // Start with Essential, AI will guide the user
    setSaving(true);
    try {
      await setMode('essential', 'onboarding_ai_decide');
      if (isOnboarding) {
        await completeOnboarding();
      }
      onClose();
    } catch (e) {
      console.error('Failed to set mode:', e);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal 
      visible={visible} 
      animationType="slide" 
      transparent
      onRequestClose={!isOnboarding ? onClose : undefined}
    >
      <View style={[styles.overlay]}>
        <View style={[
          styles.container, 
          { backgroundColor: isDark ? '#0a0a0f' : '#fff' },
          isOnboarding && styles.fullHeight
        ]}>
          <ScrollView showsVerticalScrollIndicator={false}>
            {/* Header */}
            <View style={styles.header}>
              <Text style={[styles.title, { color: colors.textPrimary }]}>
                {isOnboarding ? 'How would you like to use Visor?' : 'Change Experience Mode'}
              </Text>
              {isOnboarding && (
                <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
                  You can change this anytime in Settings
                </Text>
              )}
            </View>
            
            {/* Mode Cards */}
            <View style={styles.modesContainer}>
              {(Object.keys(MODE_CONFIG) as ExperienceMode[]).map((key) => {
                const config = MODE_CONFIG[key];
                const isSelected = selectedMode === key;
                
                return (
                  <TouchableOpacity
                    key={key}
                    style={[
                      styles.modeCard,
                      { 
                        borderColor: isSelected ? config.color : isDark ? '#222' : '#e5e5e5',
                        backgroundColor: isSelected ? `${config.color}10` : 'transparent',
                      }
                    ]}
                    onPress={() => handleSelectMode(key)}
                    activeOpacity={0.7}
                  >
                    <View style={styles.modeHeader}>
                      <View style={[styles.modeIcon, { backgroundColor: `${config.color}20` }]}>
                        <MaterialCommunityIcons 
                          name={config.icon as any} 
                          size={24} 
                          color={config.color} 
                        />
                      </View>
                      <View style={styles.modeInfo}>
                        <Text style={[styles.modeTitle, { color: colors.textPrimary }]}>
                          {config.title}
                        </Text>
                        <Text style={[styles.modeSubtitle, { color: config.color }]}>
                          {config.subtitle}
                        </Text>
                      </View>
                      {isSelected && (
                        <MaterialCommunityIcons 
                          name="check-circle" 
                          size={24} 
                          color={config.color} 
                        />
                      )}
                    </View>
                    
                    <Text style={[styles.modeDescription, { color: colors.textSecondary }]}>
                      {config.description}
                    </Text>
                    
                    <View style={styles.featuresContainer}>
                      {config.features.map((feature, idx) => (
                        <View key={idx} style={styles.featureRow}>
                          <MaterialCommunityIcons 
                            name="check" 
                            size={16} 
                            color={config.color} 
                          />
                          <Text style={[styles.featureText, { color: colors.textSecondary }]}>
                            {feature}
                          </Text>
                        </View>
                      ))}
                    </View>
                  </TouchableOpacity>
                );
              })}
            </View>
            
            {/* AI Decide Option (Onboarding only) */}
            {isOnboarding && (
              <TouchableOpacity
                style={[
                  styles.aiDecideButton, 
                  { borderColor: isDark ? '#333' : '#ddd' }
                ]}
                onPress={handleLetAIDecide}
                disabled={saving}
              >
                <MaterialCommunityIcons name="robot" size={20} color={colors.primary} />
                <Text style={[styles.aiDecideText, { color: colors.primary }]}>
                  Not sure? Let Visor AI guide me
                </Text>
              </TouchableOpacity>
            )}
            
            {/* Action Buttons */}
            <View style={styles.actions}>
              <TouchableOpacity
                style={[styles.confirmButton, { backgroundColor: MODE_CONFIG[selectedMode].color }]}
                onPress={handleConfirm}
                disabled={saving}
              >
                {saving ? (
                  <ActivityIndicator color="#fff" size="small" />
                ) : (
                  <>
                    <Text style={styles.confirmButtonText}>
                      {isOnboarding ? `Start with ${MODE_CONFIG[selectedMode].title}` : 'Save Changes'}
                    </Text>
                    <MaterialCommunityIcons name="arrow-right" size={20} color="#fff" />
                  </>
                )}
              </TouchableOpacity>
              
              {!isOnboarding && (
                <TouchableOpacity style={styles.cancelButton} onPress={onClose}>
                  <Text style={[styles.cancelText, { color: colors.textSecondary }]}>Cancel</Text>
                </TouchableOpacity>
              )}
            </View>
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.6)',
    justifyContent: 'flex-end',
  },
  container: {
    borderTopLeftRadius: 28,
    borderTopRightRadius: 28,
    padding: 24,
    paddingBottom: 40,
    maxHeight: SCREEN_HEIGHT * 0.9,
  },
  fullHeight: {
    flex: 1,
    borderTopLeftRadius: 0,
    borderTopRightRadius: 0,
    paddingTop: 60,
  },
  header: {
    marginBottom: 24,
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
    textAlign: 'center',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 14,
    textAlign: 'center',
  },
  modesContainer: {
    gap: 16,
  },
  modeCard: {
    padding: 16,
    borderRadius: 16,
    borderWidth: 2,
  },
  modeHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  modeIcon: {
    width: 44,
    height: 44,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  modeInfo: {
    flex: 1,
  },
  modeTitle: {
    fontSize: 17,
    fontWeight: '700',
  },
  modeSubtitle: {
    fontSize: 13,
    fontWeight: '600',
    marginTop: 2,
  },
  modeDescription: {
    fontSize: 13,
    marginBottom: 12,
  },
  featuresContainer: {
    gap: 6,
  },
  featureRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  featureText: {
    fontSize: 13,
  },
  aiDecideButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    borderStyle: 'dashed',
    marginTop: 16,
    gap: 8,
  },
  aiDecideText: {
    fontWeight: '600',
    fontSize: 14,
  },
  actions: {
    marginTop: 24,
    gap: 12,
  },
  confirmButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    borderRadius: 14,
    gap: 8,
  },
  confirmButtonText: {
    color: '#fff',
    fontWeight: '700',
    fontSize: 16,
  },
  cancelButton: {
    alignItems: 'center',
    padding: 12,
  },
  cancelText: {
    fontSize: 15,
  },
});

export default ModeSelector;
