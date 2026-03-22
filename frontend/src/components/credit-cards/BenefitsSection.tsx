import React, { useState, useEffect, useCallback } from 'react';
import { View, Text, TouchableOpacity, ActivityIndicator, StyleSheet } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { apiRequest } from '../../utils/api';

const ICON_MAP: Record<string, string> = {
  'airplane': 'airplane',
  'gas-station': 'gas-station',
  'food': 'food',
  'shopping': 'shopping',
  'cash': 'cash-multiple',
  'star': 'star-circle',
  'shield-check': 'shield-check',
  'gift': 'gift',
  'percent': 'percent-circle',
  'door-open': 'door-open',
  'ticket-percent': 'ticket-percent',
  'credit-card-check': 'credit-card-check',
};

const CATEGORY_COLORS: Record<string, string> = {
  'Lounge Access': '#8B5CF6',
  'Cashback': '#10B981',
  'Reward Points': '#F59E0B',
  'Fuel Benefits': '#EF4444',
  'Travel Benefits': '#3B82F6',
  'Dining Benefits': '#EC4899',
  'Shopping Benefits': '#6366F1',
  'Insurance': '#14B8A6',
  'Milestone Benefits': '#F97316',
  'Fee Waiver': '#06B6D4',
  'Other': '#64748B',
};

interface Benefit {
  category: string;
  title: string;
  description: string;
  icon: string;
}

interface CardBenefits {
  card_id: string;
  card_name: string;
  last_four: string;
  benefits: Benefit[];
  has_benefits: boolean;
}

interface Props {
  token: string;
  isDark: boolean;
  colors: any;
  cards: any[];
}

export const BenefitsSection = ({ token, isDark, colors, cards }: Props) => {
  const [allBenefits, setAllBenefits] = useState<CardBenefits[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingCard, setLoadingCard] = useState<string | null>(null);
  const [expandedCards, setExpandedCards] = useState<Set<string>>(new Set());

  const fetchAllBenefits = useCallback(async () => {
    try {
      setLoading(true);
      const data = await apiRequest('/credit-cards/all-benefits', { token });
      setAllBenefits(data.cards || []);
      // Auto-expand first card
      if (data.cards?.length > 0) {
        setExpandedCards(new Set([data.cards[0].card_id]));
      }
    } catch (err) {
      console.error('Failed to fetch benefits:', err);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchAllBenefits();
  }, [fetchAllBenefits]);

  const fetchCardBenefits = async (cardId: string) => {
    try {
      setLoadingCard(cardId);
      await apiRequest(`/credit-cards/${cardId}/benefits`, { token });
      // Refresh all benefits after fetching individual card
      await fetchAllBenefits();
      setExpandedCards(prev => new Set([...prev, cardId]));
    } catch (err: any) {
      console.error('Failed to fetch card benefits:', err);
    } finally {
      setLoadingCard(null);
    }
  };

  const toggleCard = (cardId: string) => {
    setExpandedCards(prev => {
      const next = new Set(prev);
      if (next.has(cardId)) next.delete(cardId);
      else next.add(cardId);
      return next;
    });
  };

  if (loading) {
    return (
      <View style={[s.loadingWrap, { backgroundColor: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.02)' }]}>
        <ActivityIndicator size="large" color="#6366F1" />
        <Text style={[s.loadingText, { color: colors.textSecondary }]}>Loading card benefits...</Text>
      </View>
    );
  }

  if (!allBenefits.length) {
    return (
      <View style={[s.emptyWrap, { backgroundColor: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.02)' }]}>
        <MaterialCommunityIcons name="card-off-outline" size={48} color={colors.textSecondary} />
        <Text style={[s.emptyTitle, { color: colors.textPrimary }]}>No Credit Cards Found</Text>
        <Text style={[s.emptyText, { color: colors.textSecondary }]}>
          Add a credit card to see its rewards and benefits
        </Text>
      </View>
    );
  }

  return (
    <View data-testid="benefits-section">
      {allBenefits.map((card) => {
        const isExpanded = expandedCards.has(card.card_id);
        const isLoading = loadingCard === card.card_id;

        return (
          <View
            key={card.card_id}
            data-testid={`benefit-card-${card.card_id}`}
            style={[s.cardWrap, {
              backgroundColor: isDark ? 'rgba(255,255,255,0.05)' : '#fff',
              borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)',
            }]}
          >
            {/* Card Header */}
            <TouchableOpacity
              data-testid={`benefit-card-toggle-${card.card_id}`}
              style={s.cardHeader}
              onPress={() => toggleCard(card.card_id)}
            >
              <View style={s.cardHeaderLeft}>
                <MaterialCommunityIcons name="credit-card" size={22} color="#6366F1" />
                <View style={{ marginLeft: 10, flex: 1 }}>
                  <Text style={[s.cardName, { color: colors.textPrimary }]}>{card.card_name}</Text>
                  {card.last_four ? (
                    <Text style={[s.cardLast4, { color: colors.textSecondary }]}>
                      **** {card.last_four}
                    </Text>
                  ) : null}
                </View>
              </View>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                {card.has_benefits && (
                  <View style={[s.benefitCount, { backgroundColor: isDark ? 'rgba(99,102,241,0.2)' : 'rgba(99,102,241,0.1)' }]}>
                    <Text style={{ fontSize: 11, color: '#6366F1', fontWeight: '700' }}>
                      {card.benefits.length}
                    </Text>
                  </View>
                )}
                <MaterialCommunityIcons
                  name={isExpanded ? 'chevron-up' : 'chevron-down'}
                  size={22}
                  color={colors.textSecondary}
                />
              </View>
            </TouchableOpacity>

            {/* Expanded Benefits */}
            {isExpanded && (
              <View style={s.benefitsList}>
                {!card.has_benefits ? (
                  <TouchableOpacity
                    data-testid={`fetch-benefits-${card.card_id}`}
                    style={[s.fetchBtn, {
                      borderColor: '#6366F1',
                      backgroundColor: isDark ? 'rgba(99,102,241,0.1)' : 'rgba(99,102,241,0.05)',
                    }]}
                    onPress={() => fetchCardBenefits(card.card_id)}
                    disabled={isLoading}
                  >
                    {isLoading ? (
                      <>
                        <ActivityIndicator size="small" color="#6366F1" />
                        <Text style={s.fetchBtnText}>Fetching benefits with AI...</Text>
                      </>
                    ) : (
                      <>
                        <MaterialCommunityIcons name="auto-fix" size={18} color="#6366F1" />
                        <Text style={s.fetchBtnText}>Fetch Benefits with AI</Text>
                      </>
                    )}
                  </TouchableOpacity>
                ) : (
                  <>
                    {card.benefits.map((benefit, idx) => {
                      const catColor = CATEGORY_COLORS[benefit.category] || '#64748B';
                      const iconName = ICON_MAP[benefit.icon] || 'star-circle';

                      return (
                        <View
                          key={idx}
                          data-testid={`benefit-item-${card.card_id}-${idx}`}
                          style={[s.benefitItem, {
                            backgroundColor: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)',
                            borderLeftColor: catColor,
                          }]}
                        >
                          <View style={s.benefitTop}>
                            <View style={[s.benefitIcon, { backgroundColor: catColor + '20' }]}>
                              <MaterialCommunityIcons name={iconName as any} size={18} color={catColor} />
                            </View>
                            <View style={{ flex: 1 }}>
                              <Text style={[s.benefitTitle, { color: colors.textPrimary }]}>
                                {benefit.title}
                              </Text>
                              <View style={[s.catBadge, { backgroundColor: catColor + '15' }]}>
                                <Text style={[s.catBadgeText, { color: catColor }]}>
                                  {benefit.category}
                                </Text>
                              </View>
                            </View>
                          </View>
                          <Text style={[s.benefitDesc, { color: colors.textSecondary }]}>
                            {benefit.description}
                          </Text>
                        </View>
                      );
                    })}

                    {/* Refresh Button */}
                    <TouchableOpacity
                      data-testid={`refresh-benefits-${card.card_id}`}
                      style={s.refreshRow}
                      onPress={() => fetchCardBenefits(card.card_id)}
                      disabled={isLoading}
                    >
                      {isLoading ? (
                        <ActivityIndicator size="small" color={colors.textSecondary} />
                      ) : (
                        <MaterialCommunityIcons name="refresh" size={14} color={colors.textSecondary} />
                      )}
                      <Text style={[s.refreshText, { color: colors.textSecondary }]}>
                        Refresh benefits
                      </Text>
                    </TouchableOpacity>
                  </>
                )}
              </View>
            )}
          </View>
        );
      })}

      {/* AI Disclaimer */}
      <View style={[s.disclaimer, {
        backgroundColor: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)',
        borderColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)',
      }]}>
        <MaterialCommunityIcons name="information-outline" size={14} color={colors.textSecondary} />
        <Text style={[s.disclaimerText, { color: colors.textSecondary }]}>
          Benefits information is AI-generated and pulled from the web where applicable. Verify details with your card issuer for the most accurate and up-to-date information.
        </Text>
      </View>
    </View>
  );
};

const s = StyleSheet.create({
  loadingWrap: { padding: 40, borderRadius: 16, alignItems: 'center', gap: 12 },
  loadingText: { fontSize: 13, fontFamily: 'DM Sans' },
  emptyWrap: { padding: 40, borderRadius: 16, alignItems: 'center', gap: 10 },
  emptyTitle: { fontSize: 16, fontWeight: '700', fontFamily: 'DM Sans' },
  emptyText: { fontSize: 13, fontFamily: 'DM Sans', textAlign: 'center' },
  cardWrap: { borderRadius: 14, borderWidth: 1, marginBottom: 12, overflow: 'hidden' },
  cardHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', padding: 14 },
  cardHeaderLeft: { flexDirection: 'row', alignItems: 'center', flex: 1 },
  cardName: { fontSize: 15, fontWeight: '700', fontFamily: 'DM Sans' },
  cardLast4: { fontSize: 12, fontFamily: 'DM Sans', marginTop: 2 },
  benefitCount: { width: 24, height: 24, borderRadius: 12, alignItems: 'center', justifyContent: 'center' },
  benefitsList: { paddingHorizontal: 14, paddingBottom: 14 },
  fetchBtn: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8,
    paddingVertical: 14, borderRadius: 10, borderWidth: 1.5,
  },
  fetchBtnText: { fontSize: 14, fontWeight: '600', color: '#6366F1', fontFamily: 'DM Sans' },
  benefitItem: {
    borderRadius: 10, padding: 12, marginBottom: 8,
    borderLeftWidth: 3,
  },
  benefitTop: { flexDirection: 'row', alignItems: 'flex-start', gap: 10 },
  benefitIcon: { width: 34, height: 34, borderRadius: 8, alignItems: 'center', justifyContent: 'center' },
  benefitTitle: { fontSize: 14, fontWeight: '600', fontFamily: 'DM Sans', lineHeight: 20 },
  catBadge: { alignSelf: 'flex-start', paddingHorizontal: 8, paddingVertical: 2, borderRadius: 6, marginTop: 4 },
  catBadgeText: { fontSize: 10, fontWeight: '700', fontFamily: 'DM Sans' },
  benefitDesc: { fontSize: 12, fontFamily: 'DM Sans', lineHeight: 18, marginTop: 8 },
  refreshRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, paddingTop: 8 },
  refreshText: { fontSize: 12, fontFamily: 'DM Sans' },
  disclaimer: {
    flexDirection: 'row', alignItems: 'flex-start', gap: 8,
    padding: 12, borderRadius: 10, borderWidth: 1, marginTop: 4,
  },
  disclaimerText: { fontSize: 11, fontFamily: 'DM Sans', lineHeight: 16, flex: 1 },
});
