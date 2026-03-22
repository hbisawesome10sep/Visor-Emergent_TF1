/**
 * Portfolio Overview Card Component
 * Displays portfolio summary with invested amount, current value, and gain/loss
 */
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Accent } from '../../utils/theme';
import { formatINR, formatINRShort } from '../../utils/formatters';
import { type PortfolioData, ASSET_CATEGORIES } from './types';

interface PortfolioOverviewCardProps {
  portfolio: PortfolioData;
  colors: any;
  isDark: boolean;
}

export const PortfolioOverviewCard: React.FC<PortfolioOverviewCardProps> = ({
  portfolio,
  colors,
  isDark,
}) => {
  if (!portfolio || portfolio.total_invested === 0) {
    return (
      <View style={[styles.emptyPortfolio, { 
        backgroundColor: isDark ? 'rgba(10,10,11,0.9)' : '#FFFFFF', 
        borderColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)' 
      }]}>
        <MaterialCommunityIcons name="wallet-outline" size={36} color={colors.textSecondary} />
        <Text style={[styles.emptyTitle, { color: colors.textPrimary }]}>No investments yet</Text>
        <Text style={[styles.emptySubtitle, { color: colors.textSecondary }]}>
          Add investment transactions to track your portfolio
        </Text>
      </View>
    );
  }

  return (
    <View 
      data-testid="portfolio-card" 
      style={[styles.portfolioCard, {
        backgroundColor: isDark ? 'rgba(10,10,11,0.9)' : '#FFFFFF',
        borderColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)',
      }]}
    >
      {/* Summary Row */}
      <View style={styles.summaryRow}>
        <View style={{ flex: 1 }}>
          <Text style={[styles.smallLabel, { color: colors.textSecondary }]}>Invested</Text>
          <Text data-testid="portfolio-invested-value" style={[styles.mainNum, { color: colors.textPrimary }]} numberOfLines={1} adjustsFontSizeToFit minimumFontScale={0.7}>
            {formatINR(portfolio.total_invested)}
          </Text>
        </View>
        <View style={[styles.divider, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]} />
        <View style={{ flex: 1, alignItems: 'flex-end' as any }}>
          <Text style={[styles.smallLabel, { color: colors.textSecondary }]}>Current Value</Text>
          <Text data-testid="portfolio-current-value" style={[styles.mainNum, { color: colors.textPrimary }]} numberOfLines={1} adjustsFontSizeToFit minimumFontScale={0.7}>
            {formatINR(portfolio.total_current_value)}
          </Text>
        </View>
      </View>

      {/* Gain/Loss Badge */}
      <View style={[styles.gainLossBadge, {
        backgroundColor: portfolio.total_gain_loss >= 0 ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)',
      }]}>
        <MaterialCommunityIcons
          name={portfolio.total_gain_loss >= 0 ? 'trending-up' : 'trending-down'}
          size={16}
          color={portfolio.total_gain_loss >= 0 ? Accent.emerald : Accent.ruby}
        />
        <Text data-testid="portfolio-gain-loss" style={[styles.gainLossText, {
          color: portfolio.total_gain_loss >= 0 ? Accent.emerald : Accent.ruby,
        }]}>
          {portfolio.total_gain_loss >= 0 ? '+' : ''}{formatINR(portfolio.total_gain_loss)} ({portfolio.total_gain_loss >= 0 ? '+' : ''}{portfolio.total_gain_loss_pct.toFixed(2)}%)
        </Text>
      </View>

      {/* Category Breakdown Header */}
      <View style={[styles.breakdownHeader, { borderTopColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)' }]}>
        <Text style={[styles.headerText, { color: colors.textSecondary, flex: 1 }]}>Category</Text>
        <Text style={[styles.headerText, { color: colors.textSecondary, width: 80, textAlign: 'right' as any }]}>Invested</Text>
        <Text style={[styles.headerText, { color: colors.textSecondary, width: 80, textAlign: 'right' as any }]}>Current</Text>
        <Text style={[styles.headerText, { color: colors.textSecondary, width: 70, textAlign: 'right' as any }]}>Return</Text>
      </View>

      {/* Category Rows */}
      {portfolio.categories.map((cat, idx) => (
        <View 
          key={cat.category} 
          data-testid={`portfolio-cat-${cat.category}`} 
          style={[styles.categoryRow, idx < portfolio.categories.length - 1 && { 
            borderBottomWidth: 1, 
            borderBottomColor: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.03)' 
          }]}
        >
          <View style={{ flex: 1, flexDirection: 'row' as any, alignItems: 'center' as any, gap: 8 }}>
            <View style={[styles.catDot, { backgroundColor: ASSET_CATEGORIES[cat.category]?.color || '#94A3B8' }]} />
            <View>
              <Text style={[styles.catName, { color: colors.textPrimary }]}>{cat.category}</Text>
              <Text style={[styles.catTxnCount, { color: colors.textSecondary }]}>
                {cat.transactions} txn{cat.transactions > 1 ? 's' : ''}
              </Text>
            </View>
          </View>
          <Text style={[styles.catNum, { color: colors.textSecondary, width: 80 }]}>{formatINRShort(cat.invested)}</Text>
          <Text style={[styles.catNum, { color: colors.textPrimary, width: 80 }]}>{formatINRShort(cat.current_value)}</Text>
          <Text style={[styles.catReturn, { color: cat.gain_loss >= 0 ? Accent.emerald : Accent.ruby, width: 70 }]}>
            {cat.gain_loss >= 0 ? '+' : ''}{cat.gain_loss_pct.toFixed(1)}%
          </Text>
        </View>
      ))}
    </View>
  );
};

const styles = StyleSheet.create({
  portfolioCard: { 
    borderRadius: 18, 
    borderWidth: 1, 
    overflow: 'hidden', 
    marginBottom: 24 
  },
  summaryRow: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    padding: 20, 
    paddingBottom: 16 
  },
  divider: { 
    width: 1, 
    height: 40, 
    marginHorizontal: 16 
  },
  smallLabel: { 
    fontSize: 11, 
    fontFamily: 'DM Sans', 
    fontWeight: '600' as any, 
    textTransform: 'uppercase', 
    letterSpacing: 0.5 
  },
  mainNum: { 
    fontSize: 22, 
    fontFamily: 'DM Sans', 
    fontWeight: '700' as any, 
    letterSpacing: -0.5, 
    marginTop: 4 
  },
  gainLossBadge: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    gap: 8, 
    marginHorizontal: 20, 
    marginBottom: 16, 
    paddingHorizontal: 14, 
    paddingVertical: 8, 
    borderRadius: 12, 
    alignSelf: 'flex-start' 
  },
  gainLossText: { 
    fontSize: 13, 
    fontFamily: 'DM Sans', 
    fontWeight: '700' as any 
  },
  breakdownHeader: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    paddingHorizontal: 20, 
    paddingVertical: 10, 
    borderTopWidth: 1 
  },
  headerText: { 
    fontSize: 10, 
    fontFamily: 'DM Sans', 
    fontWeight: '600' as any, 
    textTransform: 'uppercase', 
    letterSpacing: 0.5 
  },
  categoryRow: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    paddingHorizontal: 20, 
    paddingVertical: 14 
  },
  catDot: { 
    width: 8, 
    height: 8, 
    borderRadius: 4 
  },
  catName: { 
    fontSize: 14, 
    fontFamily: 'DM Sans', 
    fontWeight: '600' as any 
  },
  catTxnCount: { 
    fontSize: 10, 
    fontFamily: 'DM Sans', 
    fontWeight: '500' as any, 
    marginTop: 1 
  },
  catNum: { 
    fontSize: 13, 
    fontFamily: 'DM Sans', 
    fontWeight: '600' as any, 
    textAlign: 'right' 
  },
  catReturn: { 
    fontSize: 13, 
    fontFamily: 'DM Sans', 
    fontWeight: '700' as any, 
    textAlign: 'right' 
  },
  emptyPortfolio: { 
    alignItems: 'center', 
    padding: 28, 
    borderRadius: 18, 
    borderWidth: 1, 
    marginBottom: 24 
  },
  emptyTitle: { 
    fontSize: 15, 
    fontFamily: 'DM Sans', 
    fontWeight: '700' as any, 
    marginTop: 10 
  },
  emptySubtitle: { 
    fontSize: 12, 
    marginTop: 4 
  },
});

export default PortfolioOverviewCard;
