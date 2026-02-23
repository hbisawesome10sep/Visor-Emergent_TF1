import React, { useState, useEffect } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Animated, Dimensions } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { Accent } from '../../utils/theme';
import { formatINR, formatINRShort } from '../../utils/formatters';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

interface TaxNotification {
  id: string;
  section: string;
  sectionLabel: string;
  currentAmount: number;
  limit: number;
  remaining: number;
  percentUsed: number;
  priority: 'high' | 'medium' | 'low';
  message: string;
  suggestion: string;
  icon: string;
  color: string;
}

interface SmartTaxNotificationsProps {
  autoDeductions: any;
  userDeductions: any[];
  colors: any;
  isDark: boolean;
  fyEndDate?: string;
  onDismiss?: (id: string) => void;
  onTakeAction?: (section: string) => void;
}

const SECTION_LIMITS: Record<string, { limit: number; label: string; icon: string; suggestions: string[] }> = {
  '80C': { 
    limit: 150000, 
    label: 'Investments & Insurance',
    icon: 'shield-check',
    suggestions: [
      'Invest in ELSS mutual funds for tax saving + wealth creation',
      'Pay your life insurance premium before FY end',
      'Consider PPF contribution for guaranteed returns',
      'Check if your EPF contribution is being counted'
    ]
  },
  '80D': { 
    limit: 25000, 
    label: 'Health Insurance',
    icon: 'hospital-box',
    suggestions: [
      'Buy or renew health insurance for your family',
      'Add parents to your health insurance (extra ₹50K limit)',
      'Preventive health checkup (up to ₹5,000) is included',
      'Consider super top-up plans for better coverage'
    ]
  },
  '80CCD(1B)': { 
    limit: 50000, 
    label: 'NPS Contribution',
    icon: 'piggy-bank',
    suggestions: [
      'This is additional to 80C limit - free extra deduction!',
      'Invest in NPS for retirement + tax saving',
      'NPS Tier 1 contributions qualify here',
      'Consider increasing SIP in NPS'
    ]
  },
  '80E': { 
    limit: 0, // No limit
    label: 'Education Loan Interest',
    icon: 'school',
    suggestions: [
      'Full interest amount is deductible - no limit!',
      'Available for 8 years from loan start',
      'Applies to higher education loans only'
    ]
  },
  '80G': { 
    limit: 0, // Varies
    label: 'Donations',
    icon: 'hand-heart',
    suggestions: [
      'Donate to approved NGOs/charities',
      '100% or 50% deduction based on organization',
      'Keep donation receipts with 80G certificate'
    ]
  },
  '80TTA': { 
    limit: 10000, 
    label: 'Savings Interest',
    icon: 'bank',
    suggestions: [
      'Interest from savings accounts is auto-detected',
      'Limit is ₹10,000 for individuals below 60'
    ]
  },
  '80EE': { 
    limit: 50000, 
    label: 'Home Loan Interest (First Time)',
    icon: 'home',
    suggestions: [
      'Additional to Section 24 deduction',
      'Only for first-time home buyers',
      'Loan must be sanctioned between specific dates'
    ]
  },
  '80EEA': { 
    limit: 150000, 
    label: 'Affordable Housing Interest',
    icon: 'home-city',
    suggestions: [
      'For affordable housing (stamp value ≤ ₹45 lakh)',
      'Additional to Section 24 deduction',
      'Property must be first residential property'
    ]
  },
};

const generateNotifications = (autoDeductions: any, userDeductions: any[]): TaxNotification[] => {
  const notifications: TaxNotification[] = [];
  
  // Calculate totals per section
  const sectionTotals: Record<string, number> = {};
  
  // Add auto-detected amounts
  if (autoDeductions?.sections) {
    autoDeductions.sections.forEach((section: any) => {
      sectionTotals[section.section] = (sectionTotals[section.section] || 0) + section.total_amount;
    });
  }
  
  // Add user-added amounts
  if (userDeductions) {
    userDeductions.forEach((d: any) => {
      if (d.section) {
        sectionTotals[d.section] = (sectionTotals[d.section] || 0) + (d.invested_amount || 0);
      }
    });
  }
  
  // Generate notifications for each section
  Object.entries(SECTION_LIMITS).forEach(([section, config]) => {
    if (config.limit === 0) return; // Skip unlimited sections
    
    const currentAmount = sectionTotals[section] || 0;
    const remaining = config.limit - currentAmount;
    const percentUsed = (currentAmount / config.limit) * 100;
    
    // Determine priority and message
    let priority: 'high' | 'medium' | 'low' = 'low';
    let message = '';
    let color = '#64748B';
    
    if (percentUsed >= 100) {
      // Section is maxed out - celebrate!
      return; // Don't show notification for maxed sections
    } else if (percentUsed >= 80) {
      priority = 'high';
      message = `Almost there! Just ${formatINRShort(remaining)} more to max out`;
      color = '#10B981'; // Green - close to goal
    } else if (percentUsed >= 50) {
      priority = 'medium';
      message = `Halfway done! ${formatINRShort(remaining)} remaining`;
      color = '#F59E0B'; // Amber
    } else if (percentUsed > 0) {
      priority = 'low';
      message = `Good start! ${formatINRShort(remaining)} more available`;
      color = '#3B82F6'; // Blue
    } else {
      // No utilization yet
      if (section === '80C' || section === '80D' || section === '80CCD(1B)') {
        priority = 'high';
        message = `Unused! Save up to ${formatINRShort(config.limit * 0.3)} in taxes`;
        color = '#EF4444'; // Red - attention needed
      } else {
        return; // Don't show notification for unused minor sections
      }
    }
    
    const randomSuggestion = config.suggestions[Math.floor(Math.random() * config.suggestions.length)];
    
    notifications.push({
      id: `notif-${section}`,
      section,
      sectionLabel: config.label,
      currentAmount,
      limit: config.limit,
      remaining,
      percentUsed,
      priority,
      message,
      suggestion: randomSuggestion,
      icon: config.icon,
      color,
    });
  });
  
  // Sort by priority
  const priorityOrder = { high: 0, medium: 1, low: 2 };
  notifications.sort((a, b) => priorityOrder[a.priority] - priorityOrder[b.priority]);
  
  return notifications;
};

export const SmartTaxNotifications: React.FC<SmartTaxNotificationsProps> = ({
  autoDeductions,
  userDeductions,
  colors,
  isDark,
  fyEndDate = 'March 31, 2026',
  onDismiss,
  onTakeAction,
}) => {
  const [notifications, setNotifications] = useState<TaxNotification[]>([]);
  const [dismissedIds, setDismissedIds] = useState<string[]>([]);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  
  useEffect(() => {
    const newNotifications = generateNotifications(autoDeductions, userDeductions);
    setNotifications(newNotifications.filter(n => !dismissedIds.includes(n.id)));
  }, [autoDeductions, userDeductions, dismissedIds]);
  
  const handleDismiss = (id: string) => {
    setDismissedIds(prev => [...prev, id]);
    onDismiss?.(id);
  };
  
  const highPriorityNotifs = notifications.filter(n => n.priority === 'high');
  const otherNotifs = notifications.filter(n => n.priority !== 'high');
  
  if (notifications.length === 0) return null;
  
  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <View style={[styles.headerIcon, { backgroundColor: isDark ? 'rgba(245, 158, 11, 0.2)' : 'rgba(245, 158, 11, 0.15)' }]}>
          <MaterialCommunityIcons name="bell-ring" size={16} color="#F59E0B" />
        </View>
        <View style={{ flex: 1 }}>
          <Text style={[styles.headerTitle, { color: colors.textPrimary }]}>Tax Saving Alerts</Text>
          <Text style={[styles.headerSubtitle, { color: colors.textSecondary }]}>FY ends {fyEndDate}</Text>
        </View>
        <View style={[styles.countBadge, { backgroundColor: highPriorityNotifs.length > 0 ? '#EF4444' : '#F59E0B' }]}>
          <Text style={styles.countText}>{notifications.length}</Text>
        </View>
      </View>
      
      {/* High Priority Notifications */}
      {highPriorityNotifs.map((notif) => (
        <TouchableOpacity
          key={notif.id}
          activeOpacity={0.9}
          onPress={() => setExpandedId(expandedId === notif.id ? null : notif.id)}
          data-testid={`tax-notification-${notif.section}`}
        >
          <LinearGradient
            colors={isDark 
              ? [`${notif.color}25`, `${notif.color}10`]
              : [`${notif.color}15`, `${notif.color}05`]
            }
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 0 }}
            style={[styles.notificationCard, { borderColor: `${notif.color}40` }]}
          >
            <View style={styles.notifHeader}>
              <View style={[styles.notifIcon, { backgroundColor: `${notif.color}20` }]}>
                <MaterialCommunityIcons name={notif.icon as any} size={18} color={notif.color} />
              </View>
              <View style={{ flex: 1 }}>
                <View style={styles.notifTitleRow}>
                  <Text style={[styles.notifSection, { color: notif.color }]}>{notif.section}</Text>
                  <View style={[styles.priorityBadge, { backgroundColor: `${notif.color}20` }]}>
                    <Text style={[styles.priorityText, { color: notif.color }]}>
                      {notif.priority === 'high' ? 'Action Needed' : notif.priority === 'medium' ? 'Review' : 'Tip'}
                    </Text>
                  </View>
                </View>
                <Text style={[styles.notifLabel, { color: colors.textPrimary }]}>{notif.sectionLabel}</Text>
              </View>
              <TouchableOpacity
                style={[styles.dismissBtn, { backgroundColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.05)' }]}
                onPress={() => handleDismiss(notif.id)}
              >
                <MaterialCommunityIcons name="close" size={14} color={colors.textSecondary} />
              </TouchableOpacity>
            </View>
            
            <Text style={[styles.notifMessage, { color: notif.color }]}>{notif.message}</Text>
            
            {/* Progress Bar */}
            <View style={styles.progressContainer}>
              <View style={[styles.progressTrack, { backgroundColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)' }]}>
                <View style={[styles.progressFill, { width: `${Math.min(notif.percentUsed, 100)}%`, backgroundColor: notif.color }]} />
              </View>
              <Text style={[styles.progressText, { color: colors.textSecondary }]}>
                {formatINRShort(notif.currentAmount)} / {formatINRShort(notif.limit)}
              </Text>
            </View>
            
            {/* Expanded Content */}
            {expandedId === notif.id && (
              <View style={[styles.expandedContent, { borderTopColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)' }]}>
                <View style={styles.suggestionRow}>
                  <MaterialCommunityIcons name="lightbulb-on-outline" size={16} color="#F59E0B" />
                  <Text style={[styles.suggestionText, { color: isDark ? '#FDE68A' : '#B45309' }]}>
                    {notif.suggestion}
                  </Text>
                </View>
                
                <View style={styles.potentialSaving}>
                  <Text style={[styles.savingLabel, { color: colors.textSecondary }]}>Potential Tax Savings:</Text>
                  <Text style={[styles.savingAmount, { color: Accent.emerald }]}>
                    Up to {formatINR(notif.remaining * 0.3)} (30% slab)
                  </Text>
                </View>
                
                <TouchableOpacity
                  style={[styles.actionButton, { backgroundColor: notif.color }]}
                  onPress={() => onTakeAction?.(notif.section)}
                >
                  <MaterialCommunityIcons name="plus" size={16} color="#FFF" />
                  <Text style={styles.actionButtonText}>Add {notif.section} Investment</Text>
                </TouchableOpacity>
              </View>
            )}
          </LinearGradient>
        </TouchableOpacity>
      ))}
      
      {/* Other Notifications (Collapsed) */}
      {otherNotifs.length > 0 && (
        <View style={[styles.otherNotifs, { backgroundColor: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.02)' }]}>
          <Text style={[styles.otherTitle, { color: colors.textSecondary }]}>Other Opportunities</Text>
          {otherNotifs.map((notif) => (
            <TouchableOpacity
              key={notif.id}
              style={styles.otherItem}
              onPress={() => setExpandedId(expandedId === notif.id ? null : notif.id)}
            >
              <View style={[styles.otherIcon, { backgroundColor: `${notif.color}15` }]}>
                <MaterialCommunityIcons name={notif.icon as any} size={14} color={notif.color} />
              </View>
              <Text style={[styles.otherSection, { color: notif.color }]}>{notif.section}</Text>
              <Text style={[styles.otherMessage, { color: colors.textSecondary }]} numberOfLines={1}>
                {notif.message}
              </Text>
              <MaterialCommunityIcons name="chevron-right" size={16} color={colors.textSecondary} />
            </TouchableOpacity>
          ))}
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    marginBottom: 16,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
    gap: 10,
  },
  headerIcon: {
    width: 32,
    height: 32,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerTitle: {
    fontSize: 14,
    fontFamily: 'DM Sans',
    fontWeight: '700',
  },
  headerSubtitle: {
    fontSize: 11,
    fontFamily: 'DM Sans',
    marginTop: 1,
  },
  countBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  countText: {
    color: '#FFF',
    fontSize: 12,
    fontFamily: 'DM Sans',
    fontWeight: '700',
  },
  notificationCard: {
    borderRadius: 16,
    borderWidth: 1.5,
    padding: 14,
    marginBottom: 10,
  },
  notifHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 10,
  },
  notifIcon: {
    width: 36,
    height: 36,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  notifTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  notifSection: {
    fontSize: 14,
    fontFamily: 'DM Sans',
    fontWeight: '700',
  },
  priorityBadge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 6,
  },
  priorityText: {
    fontSize: 10,
    fontFamily: 'DM Sans',
    fontWeight: '600',
  },
  notifLabel: {
    fontSize: 12,
    fontFamily: 'DM Sans',
    marginTop: 2,
  },
  dismissBtn: {
    width: 24,
    height: 24,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  notifMessage: {
    fontSize: 13,
    fontFamily: 'DM Sans',
    fontWeight: '600',
    marginTop: 10,
    marginLeft: 46,
  },
  progressContainer: {
    marginTop: 10,
    marginLeft: 46,
  },
  progressTrack: {
    height: 6,
    borderRadius: 3,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    borderRadius: 3,
  },
  progressText: {
    fontSize: 11,
    fontFamily: 'DM Sans',
    marginTop: 4,
  },
  expandedContent: {
    marginTop: 14,
    paddingTop: 14,
    borderTopWidth: 1,
    marginLeft: 46,
  },
  suggestionRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
  },
  suggestionText: {
    flex: 1,
    fontSize: 12,
    fontFamily: 'DM Sans',
    lineHeight: 18,
  },
  potentialSaving: {
    marginTop: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  savingLabel: {
    fontSize: 12,
    fontFamily: 'DM Sans',
  },
  savingAmount: {
    fontSize: 14,
    fontFamily: 'DM Sans',
    fontWeight: '700',
  },
  actionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 10,
    marginTop: 12,
    gap: 6,
  },
  actionButtonText: {
    color: '#FFF',
    fontSize: 13,
    fontFamily: 'DM Sans',
    fontWeight: '600',
  },
  otherNotifs: {
    borderRadius: 14,
    padding: 12,
  },
  otherTitle: {
    fontSize: 11,
    fontFamily: 'DM Sans',
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 8,
  },
  otherItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
    gap: 8,
  },
  otherIcon: {
    width: 28,
    height: 28,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
  },
  otherSection: {
    fontSize: 12,
    fontFamily: 'DM Sans',
    fontWeight: '700',
    width: 60,
  },
  otherMessage: {
    flex: 1,
    fontSize: 12,
    fontFamily: 'DM Sans',
  },
});
