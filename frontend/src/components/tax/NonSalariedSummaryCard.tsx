import React, { useEffect, useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ActivityIndicator } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { apiRequest } from '../../utils/api';
import { formatINRShort } from '../../utils/formatters';
import { Accent } from '../../utils/theme';

interface NonSalariedSummaryCardProps {
  token: string;
  colors: any;
  isDark: boolean;
  incomeTypes: string[];
  onOpenFreelancer: () => void;
  onOpenBusiness: () => void;
  onOpenInvestor: () => void;
  onOpenRental: () => void;
}

export const NonSalariedSummaryCard: React.FC<NonSalariedSummaryCardProps> = ({
  token, colors, isDark, incomeTypes,
  onOpenFreelancer, onOpenBusiness, onOpenInvestor, onOpenRental,
}) => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const result = await apiRequest('/tax/consolidated-income?fy=2025-26', { token });
        setData(result);
      } catch (e) {
        console.error('Consolidated income fetch error:', e);
      } finally {
        setLoading(false);
      }
    };
    if (token) fetchData();
  }, [token]);

  // Only show if user has non-salaried income types
  const hasNonSalaried = incomeTypes.some(t => ['freelancer', 'business', 'investor', 'rental'].includes(t));
  if (!hasNonSalaried) return null;

  if (loading) {
    return (
      <View style={[styles.card, { backgroundColor: isDark ? 'rgba(10,10,11,0.85)' : 'rgba(255,255,255,0.9)', borderColor: isDark ? 'rgba(139,92,246,0.15)' : 'rgba(139,92,246,0.1)' }]}>
        <ActivityIndicator size="small" color="#8B5CF6" />
      </View>
    );
  }

  const profiles = data?.profiles_available || {};
  const sources = data?.income_sources || {};

  const profileConfigs = [
    { 
      id: 'freelancer', 
      label: 'Freelancer', 
      icon: 'laptop', 
      color: '#8B5CF6',
      section: '44ADA',
      onPress: onOpenFreelancer,
    },
    { 
      id: 'business', 
      label: 'Business', 
      icon: 'store-outline', 
      color: '#F59E0B',
      section: '44AD',
      onPress: onOpenBusiness,
    },
    { 
      id: 'investor', 
      label: 'Investor', 
      icon: 'chart-line', 
      color: '#3B82F6',
      section: 'F&O/CG',
      onPress: onOpenInvestor,
    },
    { 
      id: 'rental', 
      label: 'Rental', 
      icon: 'home-outline', 
      color: Accent.emerald,
      section: 'HP',
      onPress: onOpenRental,
    },
  ];

  const relevantProfiles = profileConfigs.filter(p => incomeTypes.includes(p.id));

  return (
    <View style={[styles.card, { 
      backgroundColor: isDark ? 'rgba(10,10,11,0.85)' : 'rgba(255,255,255,0.9)',
      borderColor: isDark ? 'rgba(139,92,246,0.15)' : 'rgba(139,92,246,0.1)',
    }]}>
      {/* Header */}
      <View style={styles.header}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
          <View style={[styles.iconWrap, { backgroundColor: 'rgba(139,92,246,0.12)' }]}>
            <MaterialCommunityIcons name="account-multiple" size={18} color="#8B5CF6" />
          </View>
          <View>
            <Text style={[styles.title, { color: colors.textPrimary }]}>
              Non-Salaried Income
            </Text>
            {data?.total_taxable_income > 0 && (
              <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
                Total: {formatINRShort(data.total_taxable_income)} taxable
              </Text>
            )}
          </View>
        </View>
        {data?.recommended_itr_form && (
          <View style={[styles.itrBadge, { backgroundColor: 'rgba(245,158,11,0.1)' }]}>
            <Text style={[styles.itrText, { color: '#F59E0B' }]}>
              {data.recommended_itr_form}
            </Text>
          </View>
        )}
      </View>

      {/* Profile Cards */}
      <View style={styles.profileGrid}>
        {relevantProfiles.map(profile => {
          const isConfigured = profiles[profile.id];
          const sourceData = sources[profile.id];
          
          return (
            <TouchableOpacity
              key={profile.id}
              data-testid={`${profile.id}-profile-card`}
              style={[styles.profileCard, {
                backgroundColor: isConfigured 
                  ? `${profile.color}10`
                  : isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)',
                borderColor: isConfigured ? `${profile.color}30` : 'transparent',
              }]}
              onPress={profile.onPress}
              activeOpacity={0.7}
            >
              <View style={styles.profileTop}>
                <View style={[styles.profileIcon, { backgroundColor: `${profile.color}15` }]}>
                  <MaterialCommunityIcons name={profile.icon as any} size={16} color={profile.color} />
                </View>
                {isConfigured ? (
                  <MaterialCommunityIcons name="check-circle" size={14} color={Accent.emerald} />
                ) : (
                  <MaterialCommunityIcons name="plus-circle-outline" size={14} color={colors.textSecondary} />
                )}
              </View>
              
              <Text style={[styles.profileLabel, { color: colors.textPrimary }]}>
                {profile.label}
              </Text>
              <Text style={[styles.profileSection, { color: colors.textSecondary }]}>
                {profile.section}
              </Text>
              
              {sourceData && (
                <Text style={[styles.profileAmount, { color: profile.color }]}>
                  {formatINRShort(sourceData.taxable || 0)}
                </Text>
              )}
              {!isConfigured && (
                <Text style={[styles.profileHint, { color: colors.textSecondary }]}>
                  Tap to set up
                </Text>
              )}
            </TouchableOpacity>
          );
        })}
      </View>

      {/* Consolidated Summary */}
      {data && Object.keys(sources).length > 1 && (
        <View style={[styles.consolidatedRow, { backgroundColor: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)' }]}>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
            <MaterialCommunityIcons name="sigma" size={14} color={colors.textSecondary} />
            <Text style={[styles.consolidatedLabel, { color: colors.textSecondary }]}>
              Consolidated Taxable
            </Text>
          </View>
          <Text style={[styles.consolidatedValue, { color: '#8B5CF6' }]}>
            {formatINRShort(data.total_taxable_income || 0)}
          </Text>
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    borderRadius: 14,
    padding: 14,
    borderWidth: 1,
    marginBottom: 14,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 14,
  },
  iconWrap: {
    width: 36,
    height: 36,
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
  },
  title: {
    fontSize: 13,
    fontFamily: 'DM Sans',
    fontWeight: '700',
  },
  subtitle: {
    fontSize: 11,
    fontFamily: 'DM Sans',
    marginTop: 2,
  },
  itrBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
  },
  itrText: {
    fontSize: 10,
    fontFamily: 'DM Sans',
    fontWeight: '700',
  },
  profileGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
    marginBottom: 10,
  },
  profileCard: {
    flex: 1,
    minWidth: '45%',
    padding: 12,
    borderRadius: 12,
    borderWidth: 1,
  },
  profileTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  profileIcon: {
    width: 28,
    height: 28,
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
  },
  profileLabel: {
    fontSize: 12,
    fontFamily: 'DM Sans',
    fontWeight: '700',
  },
  profileSection: {
    fontSize: 10,
    fontFamily: 'DM Sans',
    marginTop: 2,
  },
  profileAmount: {
    fontSize: 14,
    fontFamily: 'DM Sans',
    fontWeight: '700',
    marginTop: 6,
  },
  profileHint: {
    fontSize: 10,
    fontFamily: 'DM Sans',
    fontStyle: 'italic',
    marginTop: 4,
  },
  consolidatedRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 10,
    borderRadius: 10,
  },
  consolidatedLabel: {
    fontSize: 11,
    fontFamily: 'DM Sans',
  },
  consolidatedValue: {
    fontSize: 14,
    fontFamily: 'DM Sans',
    fontWeight: '700',
  },
});
