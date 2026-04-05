// /app/frontend/src/components/experience/FeatureGate.tsx
/**
 * Feature Gate Component
 * Conditionally renders content based on user's experience mode
 */

import React, { ReactNode } from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useExperienceMode, ExperienceMode } from '../../context/ExperienceModeContext';
import { useTheme } from '../../context/ThemeContext';

interface FeatureGateProps {
  featureId: string;
  children: ReactNode;
  fallback?: ReactNode;
  showUpgradePrompt?: boolean;
  upgradeMessage?: string;
  compact?: boolean;
}

const MODE_NAMES: Record<ExperienceMode, string> = {
  essential: 'Essential',
  plus: 'Plus',
  full: 'Full'
};

export function FeatureGate({ 
  featureId, 
  children, 
  fallback,
  showUpgradePrompt = true,
  upgradeMessage,
  compact = false
}: FeatureGateProps) {
  const { isFeatureAvailable, mode, setMode, loading } = useExperienceMode();
  const { colors, isDark } = useTheme();
  
  // While loading, show children to prevent flicker
  if (loading) {
    return <>{children}</>;
  }
  
  if (isFeatureAvailable(featureId)) {
    return <>{children}</>;
  }
  
  if (fallback) {
    return <>{fallback}</>;
  }
  
  if (!showUpgradePrompt) {
    return null;
  }
  
  // Determine target mode for upgrade
  const targetMode: ExperienceMode = mode === 'essential' ? 'plus' : 'full';
  const targetModeName = MODE_NAMES[targetMode];
  
  const handleUpgrade = () => {
    setMode(targetMode, 'feature_gate');
  };
  
  if (compact) {
    return (
      <TouchableOpacity 
        style={[styles.compactPrompt, { backgroundColor: isDark ? '#1a1a2e' : '#f5f5ff' }]}
        onPress={handleUpgrade}
      >
        <MaterialCommunityIcons name="lock-outline" size={16} color={colors.primary} />
        <Text style={[styles.compactText, { color: colors.primary }]}>
          Unlock with {targetModeName}
        </Text>
      </TouchableOpacity>
    );
  }
  
  return (
    <View style={[styles.upgradePrompt, { backgroundColor: isDark ? '#1a1a2e' : '#f5f5ff' }]}>
      <View style={[styles.iconContainer, { backgroundColor: `${colors.primary}20` }]}>
        <MaterialCommunityIcons name="lock-outline" size={28} color={colors.primary} />
      </View>
      <Text style={[styles.upgradeTitle, { color: colors.textPrimary }]}>
        Feature Locked
      </Text>
      <Text style={[styles.upgradeText, { color: colors.textSecondary }]}>
        {upgradeMessage || `This feature is available in ${targetModeName} mode`}
      </Text>
      <TouchableOpacity 
        style={[styles.upgradeButton, { backgroundColor: colors.primary }]}
        onPress={handleUpgrade}
      >
        <Text style={styles.upgradeButtonText}>Upgrade to {targetModeName}</Text>
        <MaterialCommunityIcons name="arrow-right" size={18} color="#fff" />
      </TouchableOpacity>
    </View>
  );
}

/**
 * Higher-Order Component version for wrapping entire components
 */
export function withFeatureGate<P extends object>(
  WrappedComponent: React.ComponentType<P>,
  featureId: string,
  FallbackComponent?: React.ComponentType<P>
) {
  return function FeatureGatedComponent(props: P) {
    const { isFeatureAvailable, loading } = useExperienceMode();
    
    if (loading || isFeatureAvailable(featureId)) {
      return <WrappedComponent {...props} />;
    }
    
    if (FallbackComponent) {
      return <FallbackComponent {...props} />;
    }
    
    return null;
  };
}

/**
 * Hook for programmatic feature checks
 */
export function useFeatureAccess(featureId: string) {
  const { isFeatureAvailable, mode, checkFeatureAccess } = useExperienceMode();
  
  return {
    available: isFeatureAvailable(featureId),
    currentMode: mode,
    checkAccess: () => checkFeatureAccess(featureId)
  };
}

const styles = StyleSheet.create({
  upgradePrompt: {
    padding: 24,
    borderRadius: 16,
    alignItems: 'center',
    margin: 16,
  },
  iconContainer: {
    width: 56,
    height: 56,
    borderRadius: 28,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
  },
  upgradeTitle: {
    fontSize: 18,
    fontWeight: '700',
    marginBottom: 8,
  },
  upgradeText: {
    marginBottom: 20,
    textAlign: 'center',
    fontSize: 14,
    lineHeight: 20,
  },
  upgradeButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 24,
    paddingVertical: 14,
    borderRadius: 12,
  },
  upgradeButtonText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 15,
  },
  compactPrompt: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
  },
  compactText: {
    fontSize: 13,
    fontWeight: '500',
  },
});

export default FeatureGate;
