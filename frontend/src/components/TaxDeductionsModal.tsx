/**
 * Tax Deductions Browser Modal
 * Shows all Chapter VI deductions from Indian Income Tax Act
 * with detailed explanations and examples
 */

import React, { useState, useCallback } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, Modal, ScrollView,
  TextInput, Dimensions, Platform, Alert,
} from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { TAX_DEDUCTIONS, TaxDeduction, getPopularDeductions, searchDeductions } from '../data/taxDeductions';
import { Accent } from '../utils/theme';
import { formatINR } from '../utils/formatters';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

type Props = {
  visible: boolean;
  onClose: () => void;
  onAddDeduction: (deduction: TaxDeduction) => void;
  colors: any;
  isDark: boolean;
  userDeductions?: string[]; // IDs of deductions user already has
};

const CATEGORIES = [
  { key: 'all', label: 'All', icon: 'view-grid' },
  { key: 'popular', label: 'Popular', icon: 'star' },
  { key: 'investments', label: 'Investments', icon: 'chart-line' },
  { key: 'insurance', label: 'Insurance', icon: 'shield-check' },
  { key: 'savings', label: 'Savings', icon: 'piggy-bank' },
  { key: 'housing', label: 'Housing', icon: 'home' },
  { key: 'loans', label: 'Loans', icon: 'bank' },
  { key: 'medical', label: 'Medical', icon: 'medical-bag' },
  { key: 'donations', label: 'Donations', icon: 'hand-heart' },
];

export default function TaxDeductionsModal({
  visible,
  onClose,
  onAddDeduction,
  colors,
  isDark,
  userDeductions = [],
}: Props) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('popular');
  const [selectedDeduction, setSelectedDeduction] = useState<TaxDeduction | null>(null);
  const [showDetailModal, setShowDetailModal] = useState(false);

  // Filter deductions based on search and category
  const getFilteredDeductions = useCallback(() => {
    let deductions = TAX_DEDUCTIONS;

    if (searchQuery.trim()) {
      deductions = searchDeductions(searchQuery);
    } else if (selectedCategory === 'popular') {
      deductions = getPopularDeductions();
    } else if (selectedCategory !== 'all') {
      deductions = TAX_DEDUCTIONS.filter(d => d.category === selectedCategory);
    }

    return deductions;
  }, [searchQuery, selectedCategory]);

  const handleSelectDeduction = (deduction: TaxDeduction) => {
    setSelectedDeduction(deduction);
    setShowDetailModal(true);
  };

  const handleAddDeduction = () => {
    if (selectedDeduction) {
      if (userDeductions.includes(selectedDeduction.id)) {
        Alert.alert('Already Added', 'This deduction is already in your tax planning.');
      } else {
        onAddDeduction(selectedDeduction);
        setShowDetailModal(false);
        Alert.alert(
          'Deduction Added',
          `${selectedDeduction.name} has been added to your Tax Planning. Related transactions will be auto-categorized.`
        );
      }
    }
  };

  const getCategoryIcon = (category: string): string => {
    const icons: Record<string, string> = {
      investments: 'chart-line',
      insurance: 'shield-check',
      savings: 'piggy-bank',
      loans: 'bank',
      donations: 'hand-heart',
      housing: 'home',
      medical: 'medical-bag',
      other: 'tag',
    };
    return icons[category] || 'file-document';
  };

  const filteredDeductions = getFilteredDeductions();

  return (
    <>
      {/* Main Browser Modal */}
      <Modal visible={visible} animationType="slide" transparent={false} onRequestClose={onClose}>
        <View style={[styles.container, { backgroundColor: colors.background }]}>
          {/* Header */}
          <View style={[styles.header, {
            backgroundColor: isDark ? '#000' : '#fff',
            borderBottomColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)',
          }]}>
            <View style={styles.headerLeft}>
              <LinearGradient
                colors={['#F97316', '#EA580C']}
                style={styles.headerIcon}
              >
                <MaterialCommunityIcons name="file-document-multiple" size={22} color="#fff" />
              </LinearGradient>
              <View>
                <Text style={[styles.headerTitle, { color: colors.textPrimary }]}>Tax Deductions</Text>
                <Text style={[styles.headerSubtitle, { color: colors.textSecondary }]}>
                  Chapter VI-A • FY 2025-26
                </Text>
              </View>
            </View>
            <TouchableOpacity
              style={[styles.closeBtn, { backgroundColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.05)' }]}
              onPress={onClose}
            >
              <MaterialCommunityIcons name="close" size={22} color={colors.textSecondary} />
            </TouchableOpacity>
          </View>

          {/* Search Bar */}
          <View style={[styles.searchContainer, {
            backgroundColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)',
          }]}>
            <MaterialCommunityIcons name="magnify" size={20} color={colors.textSecondary} />
            <TextInput
              style={[styles.searchInput, { color: colors.textPrimary }]}
              placeholder="Search deductions..."
              placeholderTextColor={colors.textSecondary}
              value={searchQuery}
              onChangeText={setSearchQuery}
            />
            {searchQuery.length > 0 && (
              <TouchableOpacity onPress={() => setSearchQuery('')}>
                <MaterialCommunityIcons name="close-circle" size={18} color={colors.textSecondary} />
              </TouchableOpacity>
            )}
          </View>

          {/* Category Pills */}
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            style={styles.categoryScrollWrapper}
            contentContainerStyle={styles.categoryScroll}
          >
            {CATEGORIES.map(cat => (
              <TouchableOpacity
                key={cat.key}
                style={[
                  styles.categoryPill,
                  {
                    backgroundColor: selectedCategory === cat.key
                      ? '#F97316'
                      : isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.05)',
                  },
                ]}
                onPress={() => setSelectedCategory(cat.key)}
              >
                <MaterialCommunityIcons
                  name={cat.icon as any}
                  size={14}
                  color={selectedCategory === cat.key ? '#fff' : colors.textSecondary}
                />
                <Text style={[
                  styles.categoryText,
                  { color: selectedCategory === cat.key ? '#fff' : colors.textPrimary },
                ]}>
                  {cat.label}
                </Text>
              </TouchableOpacity>
            ))}
          </ScrollView>

          {/* Deductions List */}
          <ScrollView
            style={styles.list}
            contentContainerStyle={styles.listContent}
            showsVerticalScrollIndicator={false}
          >
            <Text style={[styles.sectionLabel, { color: colors.textSecondary }]}>
              {filteredDeductions.length} deductions found
            </Text>

            {filteredDeductions.map(deduction => {
              const isAdded = userDeductions.includes(deduction.id);
              return (
                <TouchableOpacity
                  key={deduction.id}
                  style={[styles.deductionCard, {
                    backgroundColor: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.03)',
                    borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
                  }]}
                  onPress={() => handleSelectDeduction(deduction)}
                  activeOpacity={0.7}
                >
                  <View style={styles.deductionHeader}>
                    <View style={[styles.deductionIcon, {
                      backgroundColor: isDark ? 'rgba(249,115,22,0.15)' : 'rgba(249,115,22,0.1)',
                    }]}>
                      <MaterialCommunityIcons
                        name={deduction.icon as any}
                        size={20}
                        color="#F97316"
                      />
                    </View>
                    <View style={styles.deductionInfo}>
                      <View style={styles.deductionTitleRow}>
                        <Text style={[styles.deductionSection, { color: '#F97316' }]}>
                          {deduction.section}
                        </Text>
                        {isAdded && (
                          <View style={styles.addedBadge}>
                            <MaterialCommunityIcons name="check" size={10} color="#fff" />
                            <Text style={styles.addedText}>Added</Text>
                          </View>
                        )}
                      </View>
                      <Text style={[styles.deductionName, { color: colors.textPrimary }]} numberOfLines={1}>
                        {deduction.name}
                      </Text>
                      <Text style={[styles.deductionDesc, { color: colors.textSecondary }]} numberOfLines={2}>
                        {deduction.shortDescription}
                      </Text>
                    </View>
                    <View style={styles.deductionActions}>
                      <View style={[styles.limitBadge, {
                        backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.05)',
                      }]}>
                        <Text style={[styles.limitText, { color: colors.textPrimary }]}>
                          {deduction.limit ? `₹${(deduction.limit / 100000).toFixed(1)}L` : 'No Limit'}
                        </Text>
                      </View>
                      <TouchableOpacity
                        style={[styles.infoBtn, {
                          backgroundColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.05)',
                        }]}
                        onPress={() => handleSelectDeduction(deduction)}
                      >
                        <MaterialCommunityIcons name="information" size={18} color={colors.textSecondary} />
                      </TouchableOpacity>
                    </View>
                  </View>
                </TouchableOpacity>
              );
            })}

            {filteredDeductions.length === 0 && (
              <View style={styles.emptyState}>
                <MaterialCommunityIcons name="file-search" size={48} color={colors.textSecondary} />
                <Text style={[styles.emptyTitle, { color: colors.textPrimary }]}>
                  No deductions found
                </Text>
                <Text style={[styles.emptyText, { color: colors.textSecondary }]}>
                  Try a different search term or category
                </Text>
              </View>
            )}

            <View style={{ height: 100 }} />
          </ScrollView>
        </View>
      </Modal>

      {/* Detail Modal */}
      <Modal
        visible={showDetailModal && selectedDeduction !== null}
        animationType="slide"
        transparent
        onRequestClose={() => setShowDetailModal(false)}
      >
        <View style={styles.detailOverlay}>
          <View style={[styles.detailContent, { backgroundColor: colors.surface }]}>
            <View style={styles.detailHandle} />

            {selectedDeduction && (
              <ScrollView showsVerticalScrollIndicator={false}>
                {/* Header */}
                <View style={styles.detailHeader}>
                  <View style={[styles.detailIconLarge, {
                    backgroundColor: isDark ? 'rgba(249,115,22,0.15)' : 'rgba(249,115,22,0.1)',
                  }]}>
                    <MaterialCommunityIcons
                      name={selectedDeduction.icon as any}
                      size={32}
                      color="#F97316"
                    />
                  </View>
                  <TouchableOpacity
                    style={[styles.closeBtn, { backgroundColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.05)' }]}
                    onPress={() => setShowDetailModal(false)}
                  >
                    <MaterialCommunityIcons name="close" size={22} color={colors.textSecondary} />
                  </TouchableOpacity>
                </View>

                <View style={styles.detailBadgeRow}>
                  <View style={[styles.sectionBadge, { backgroundColor: '#F9731620' }]}>
                    <Text style={styles.sectionBadgeText}>{selectedDeduction.section}</Text>
                  </View>
                  <View style={[styles.categoryBadge, {
                    backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.05)',
                  }]}>
                    <MaterialCommunityIcons
                      name={getCategoryIcon(selectedDeduction.category)}
                      size={12}
                      color={colors.textSecondary}
                    />
                    <Text style={[styles.categoryBadgeText, { color: colors.textSecondary }]}>
                      {selectedDeduction.category.charAt(0).toUpperCase() + selectedDeduction.category.slice(1)}
                    </Text>
                  </View>
                </View>

                <Text style={[styles.detailTitle, { color: colors.textPrimary }]}>
                  {selectedDeduction.name}
                </Text>

                {/* Limit Info */}
                <View style={[styles.limitCard, {
                  backgroundColor: isDark ? 'rgba(249,115,22,0.1)' : 'rgba(249,115,22,0.08)',
                  borderColor: isDark ? 'rgba(249,115,22,0.2)' : 'rgba(249,115,22,0.15)',
                }]}>
                  <MaterialCommunityIcons name="information" size={18} color="#F97316" />
                  <Text style={[styles.limitCardText, { color: colors.textPrimary }]}>
                    {selectedDeduction.limit
                      ? `Maximum deduction: ${formatINR(selectedDeduction.limit)}`
                      : 'No upper limit on this deduction'
                    }
                  </Text>
                </View>

                {/* Full Description */}
                <View style={styles.detailSection}>
                  <Text style={[styles.detailSectionTitle, { color: colors.textPrimary }]}>
                    What is this deduction?
                  </Text>
                  <Text style={[styles.detailText, { color: colors.textSecondary }]}>
                    {selectedDeduction.fullDescription}
                  </Text>
                </View>

                {/* Example */}
                <View style={[styles.exampleCard, {
                  backgroundColor: isDark ? 'rgba(16,185,129,0.1)' : 'rgba(16,185,129,0.08)',
                  borderColor: isDark ? 'rgba(16,185,129,0.2)' : 'rgba(16,185,129,0.15)',
                }]}>
                  <View style={styles.exampleHeader}>
                    <MaterialCommunityIcons name="lightbulb-on" size={18} color={Accent.emerald} />
                    <Text style={[styles.exampleTitle, { color: Accent.emerald }]}>Example</Text>
                  </View>
                  <Text style={[styles.exampleText, { color: colors.textPrimary }]}>
                    {selectedDeduction.example}
                  </Text>
                </View>

                {/* Eligibility */}
                <View style={styles.detailSection}>
                  <Text style={[styles.detailSectionTitle, { color: colors.textPrimary }]}>
                    Who is eligible?
                  </Text>
                  <Text style={[styles.detailText, { color: colors.textSecondary }]}>
                    {selectedDeduction.eligibility}
                  </Text>
                </View>

                {/* Documents Required */}
                <View style={styles.detailSection}>
                  <Text style={[styles.detailSectionTitle, { color: colors.textPrimary }]}>
                    Documents Required
                  </Text>
                  {selectedDeduction.documents.map((doc, idx) => (
                    <View key={idx} style={styles.documentRow}>
                      <MaterialCommunityIcons name="check-circle" size={16} color={Accent.emerald} />
                      <Text style={[styles.documentText, { color: colors.textSecondary }]}>{doc}</Text>
                    </View>
                  ))}
                </View>

                {/* Add Button */}
                <TouchableOpacity
                  style={[styles.addButton, {
                    backgroundColor: userDeductions.includes(selectedDeduction.id) ? colors.border : '#F97316',
                  }]}
                  onPress={handleAddDeduction}
                  disabled={userDeductions.includes(selectedDeduction.id)}
                >
                  <MaterialCommunityIcons
                    name={userDeductions.includes(selectedDeduction.id) ? 'check' : 'plus'}
                    size={20}
                    color="#fff"
                  />
                  <Text style={styles.addButtonText}>
                    {userDeductions.includes(selectedDeduction.id)
                      ? 'Already Added'
                      : 'Add to My Tax Planning'
                    }
                  </Text>
                </TouchableOpacity>

                <View style={{ height: 40 }} />
              </ScrollView>
            )}
          </View>
        </View>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingTop: Platform.OS === 'ios' ? 60 : 16,
    paddingBottom: 12,
    borderBottomWidth: 1,
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  headerIcon: {
    width: 40,
    height: 40,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
  },
  headerTitle: {
    fontSize: 18,
    fontFamily: 'DM Sans',
    fontWeight: '700',
  },
  headerSubtitle: {
    fontSize: 12,
  },
  closeBtn: {
    width: 36,
    height: 36,
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
  },
  searchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginHorizontal: 16,
    marginTop: 12,
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderRadius: 12,
    gap: 8,
  },
  searchInput: {
    flex: 1,
    fontSize: 15,
    fontFamily: 'DM Sans',
  },
  categoryScroll: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    flexDirection: 'row',
    alignItems: 'center',
  },
  categoryPill: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 24,
    marginRight: 10,
    height: 40,
    minWidth: 'auto' as any,
  },
  categoryText: {
    fontSize: 13,
    fontFamily: 'DM Sans',
    fontWeight: '600',
    marginLeft: 6,
  },
  list: {
    flex: 1,
  },
  listContent: {
    paddingHorizontal: 16,
    paddingBottom: 100,
  },
  sectionLabel: {
    fontSize: 12,
    fontFamily: 'DM Sans',
    marginBottom: 12,
  },
  deductionCard: {
    borderRadius: 16,
    padding: 14,
    marginBottom: 10,
    borderWidth: 1,
  },
  deductionHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
  },
  deductionIcon: {
    width: 44,
    height: 44,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
  },
  deductionInfo: {
    flex: 1,
  },
  deductionTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 2,
  },
  deductionSection: {
    fontSize: 11,
    fontFamily: 'DM Sans',
    fontWeight: '700',
  },
  addedBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Accent.emerald,
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 8,
    gap: 2,
  },
  addedText: {
    fontSize: 9,
    fontFamily: 'DM Sans',
    fontWeight: '600',
    color: '#fff',
  },
  deductionName: {
    fontSize: 15,
    fontFamily: 'DM Sans',
    fontWeight: '600',
    marginBottom: 4,
  },
  deductionDesc: {
    fontSize: 12,
    fontFamily: 'DM Sans',
    lineHeight: 16,
  },
  deductionActions: {
    alignItems: 'flex-end',
    gap: 8,
  },
  limitBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
  },
  limitText: {
    fontSize: 11,
    fontFamily: 'DM Sans',
    fontWeight: '600',
  },
  infoBtn: {
    width: 32,
    height: 32,
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
  },
  emptyState: {
    alignItems: 'center',
    paddingTop: 60,
    gap: 12,
  },
  emptyTitle: {
    fontSize: 16,
    fontFamily: 'DM Sans',
    fontWeight: '600',
  },
  emptyText: {
    fontSize: 13,
    fontFamily: 'DM Sans',
  },

  // Detail Modal
  detailOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'flex-end',
  },
  detailContent: {
    borderTopLeftRadius: 28,
    borderTopRightRadius: 28,
    paddingHorizontal: 20,
    paddingTop: 8,
    maxHeight: '90%',
  },
  detailHandle: {
    width: 40,
    height: 4,
    borderRadius: 2,
    backgroundColor: '#CBD5E1',
    alignSelf: 'center',
    marginBottom: 16,
  },
  detailHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 16,
  },
  detailIconLarge: {
    width: 60,
    height: 60,
    borderRadius: 16,
    justifyContent: 'center',
    alignItems: 'center',
  },
  detailBadgeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 8,
  },
  sectionBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 8,
  },
  sectionBadgeText: {
    fontSize: 12,
    fontFamily: 'DM Sans',
    fontWeight: '700',
    color: '#F97316',
  },
  categoryBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
    gap: 4,
  },
  categoryBadgeText: {
    fontSize: 11,
    fontFamily: 'DM Sans',
    fontWeight: '500',
  },
  detailTitle: {
    fontSize: 22,
    fontFamily: 'DM Sans',
    fontWeight: '700',
    marginBottom: 16,
    letterSpacing: -0.5,
  },
  limitCard: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 14,
    borderRadius: 12,
    borderWidth: 1,
    gap: 10,
    marginBottom: 20,
  },
  limitCardText: {
    flex: 1,
    fontSize: 14,
    fontFamily: 'DM Sans',
    fontWeight: '500',
  },
  detailSection: {
    marginBottom: 20,
  },
  detailSectionTitle: {
    fontSize: 15,
    fontFamily: 'DM Sans',
    fontWeight: '700',
    marginBottom: 8,
  },
  detailText: {
    fontSize: 14,
    fontFamily: 'DM Sans',
    lineHeight: 22,
  },
  exampleCard: {
    padding: 16,
    borderRadius: 14,
    borderWidth: 1,
    marginBottom: 20,
  },
  exampleHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 10,
  },
  exampleTitle: {
    fontSize: 14,
    fontFamily: 'DM Sans',
    fontWeight: '700',
  },
  exampleText: {
    fontSize: 14,
    fontFamily: 'DM Sans',
    lineHeight: 22,
  },
  documentRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    marginBottom: 8,
  },
  documentText: {
    fontSize: 13,
    fontFamily: 'DM Sans',
    flex: 1,
  },
  addButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    height: 56,
    borderRadius: 16,
    gap: 8,
    marginTop: 10,
  },
  addButtonText: {
    fontSize: 16,
    fontFamily: 'DM Sans',
    fontWeight: '700',
    color: '#fff',
  },
});
