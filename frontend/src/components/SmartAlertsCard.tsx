import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { formatINRShort } from '../utils/formatters';
import { Accent } from '../utils/theme';

type Alert = {
  id: string;
  type: 'warning' | 'success' | 'info' | 'critical';
  icon: string;
  title: string;
  message: string;
  action?: string;
  value?: string;
};

type Props = {
  alerts: Alert[];
  isDark: boolean;
  colors: any;
  onAlertPress?: (alert: Alert) => void;
};

export const SmartAlertsCard = ({ alerts, isDark, colors, onAlertPress }: Props) => {
  if (!alerts || alerts.length === 0) return null;

  const typeStyles = {
    critical: {
      bg: isDark ? 'rgba(239, 68, 68, 0.12)' : 'rgba(239, 68, 68, 0.08)',
      border: Accent.ruby,
      iconBg: 'rgba(239, 68, 68, 0.2)',
    },
    warning: {
      bg: isDark ? 'rgba(245, 158, 11, 0.12)' : 'rgba(245, 158, 11, 0.08)',
      border: Accent.amber,
      iconBg: 'rgba(245, 158, 11, 0.2)',
    },
    success: {
      bg: isDark ? 'rgba(16, 185, 129, 0.12)' : 'rgba(16, 185, 129, 0.08)',
      border: Accent.emerald,
      iconBg: 'rgba(16, 185, 129, 0.2)',
    },
    info: {
      bg: isDark ? 'rgba(59, 130, 246, 0.12)' : 'rgba(59, 130, 246, 0.08)',
      border: Accent.sapphire,
      iconBg: 'rgba(59, 130, 246, 0.2)',
    },
  };

  const typeColors = {
    critical: Accent.ruby,
    warning: Accent.amber,
    success: Accent.emerald,
    info: Accent.sapphire,
  };

  // Sort alerts by priority (critical > warning > info > success)
  const priorityOrder = { critical: 0, warning: 1, info: 2, success: 3 };
  const sortedAlerts = [...alerts].sort((a, b) => priorityOrder[a.type] - priorityOrder[b.type]);

  return (
    <View style={[styles.container, {
      backgroundColor: isDark ? 'rgba(10, 10, 11, 0.9)' : 'rgba(255, 255, 255, 0.95)',
      borderColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)',
    }]}>
      <View style={styles.header}>
        <View style={[styles.headerIcon, { backgroundColor: isDark ? 'rgba(99, 102, 241, 0.15)' : 'rgba(99, 102, 241, 0.1)' }]}>
          <MaterialCommunityIcons name="bell-ring" size={20} color="#6366F1" />
        </View>
        <View style={{ flex: 1 }}>
          <Text style={[styles.title, { color: colors.textPrimary }]}>Smart Alerts</Text>
          <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
            {alerts.filter(a => a.type === 'critical' || a.type === 'warning').length} items need attention
          </Text>
        </View>
        <View style={[styles.badge, { backgroundColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.06)' }]}>
          <Text style={[styles.badgeText, { color: colors.textSecondary }]}>{alerts.length}</Text>
        </View>
      </View>

      <View style={styles.alertsList}>
        {sortedAlerts.map((alert, index) => {
          const style = typeStyles[alert.type];
          const color = typeColors[alert.type];
          
          return (
            <TouchableOpacity 
              key={alert.id}
              style={[styles.alertItem, { 
                backgroundColor: style.bg,
                borderLeftColor: style.border,
              }]}
              onPress={() => onAlertPress?.(alert)}
              activeOpacity={0.7}
            >
              <View style={[styles.alertIcon, { backgroundColor: style.iconBg }]}>
                <MaterialCommunityIcons name={alert.icon as any} size={18} color={color} />
              </View>
              <View style={styles.alertContent}>
                <Text style={[styles.alertTitle, { color: colors.textPrimary }]}>{alert.title}</Text>
                <Text style={[styles.alertMessage, { color: colors.textSecondary }]} numberOfLines={2}>
                  {alert.message}
                </Text>
                {alert.value && (
                  <Text style={[styles.alertValue, { color }]}>{alert.value}</Text>
                )}
              </View>
              {alert.action && (
                <View style={[styles.actionBtn, { backgroundColor: `${color}20` }]}>
                  <Text style={[styles.actionText, { color }]}>{alert.action}</Text>
                  <MaterialCommunityIcons name="chevron-right" size={14} color={color} />
                </View>
              )}
            </TouchableOpacity>
          );
        })}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    borderRadius: 20,
    borderWidth: 1,
    padding: 20,
    marginBottom: 16,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 16,
  },
  headerIcon: {
    width: 40,
    height: 40,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  title: {
    fontSize: 18,
    fontFamily: 'DM Sans',
    fontWeight: '700' as any,
  },
  subtitle: {
    fontSize: 12,
    fontFamily: 'DM Sans',
    marginTop: 2,
  },
  badge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  badgeText: {
    fontSize: 12,
    fontFamily: 'DM Sans',
    fontWeight: '600' as any,
  },
  alertsList: {
    gap: 10,
  },
  alertItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    borderRadius: 12,
    borderLeftWidth: 3,
    gap: 12,
  },
  alertIcon: {
    width: 36,
    height: 36,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  alertContent: {
    flex: 1,
  },
  alertTitle: {
    fontSize: 14,
    fontFamily: 'DM Sans',
    fontWeight: '600' as any,
  },
  alertMessage: {
    fontSize: 12,
    fontFamily: 'DM Sans',
    marginTop: 2,
    lineHeight: 16,
  },
  alertValue: {
    fontSize: 14,
    fontFamily: 'DM Sans',
    fontWeight: '700' as any,
    marginTop: 4,
  },
  actionBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
    gap: 2,
  },
  actionText: {
    fontSize: 11,
    fontFamily: 'DM Sans',
    fontWeight: '600' as any,
  },
});
