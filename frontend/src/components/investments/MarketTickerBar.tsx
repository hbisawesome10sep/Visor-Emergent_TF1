import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ScrollView } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Accent } from '../../utils/theme';

interface MarketItem {
  key: string;
  name: string;
  price: number;
  change: number;
  change_percent: number;
  icon: string;
}

interface MarketTickerBarProps {
  marketData: MarketItem[];
  colors: any;
  isDark: boolean;
}

const getMarketIcon = (key: string): any => {
  const icons: Record<string, any> = {
    'nifty_50': 'chart-line',
    'sensex': 'chart-areaspline',
    'nifty_bank': 'bank',
    'gold_10g': 'gold',
    'silver_1kg': 'shape-circle-plus',
  };
  return icons[key] || 'chart-line';
};

export const MarketTickerBar: React.FC<MarketTickerBarProps> = ({ marketData, colors, isDark }) => {
  if (!marketData?.length) return null;

  return (
    <View data-testid="market-ticker-bar" style={styles.container}>
      <ScrollView 
        horizontal 
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.scrollContent}
      >
        {marketData.map((item) => {
          const isUp = item.change >= 0;
          const changeColor = isUp ? Accent.emerald : Accent.ruby;
          
          return (
            <View 
              key={item.key}
              data-testid={`market-item-${item.key}`}
              style={[styles.tickerItem, { 
                backgroundColor: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.03)',
                borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.05)',
              }]}
            >
              <View style={[styles.iconWrap, { 
                backgroundColor: isDark ? 'rgba(99,102,241,0.15)' : 'rgba(99,102,241,0.1)' 
              }]}>
                <MaterialCommunityIcons 
                  name={getMarketIcon(item.key)} 
                  size={16} 
                  color={Accent.amethyst} 
                />
              </View>
              <View style={styles.tickerContent}>
                <Text style={[styles.tickerName, { color: colors.textSecondary }]} numberOfLines={1}>
                  {item.name}
                </Text>
                <Text style={[styles.tickerPrice, { color: colors.textPrimary }]}>
                  {item.price >= 100000 
                    ? `₹${(item.price / 1000).toFixed(1)}K` 
                    : `₹${item.price.toLocaleString('en-IN')}`}
                </Text>
              </View>
              <View style={[styles.changeBadge, { 
                backgroundColor: isUp ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)' 
              }]}>
                <MaterialCommunityIcons 
                  name={isUp ? 'arrow-up' : 'arrow-down'} 
                  size={10} 
                  color={changeColor} 
                />
                <Text style={[styles.changeText, { color: changeColor }]}>
                  {Math.abs(item.change_percent).toFixed(2)}%
                </Text>
              </View>
            </View>
          );
        })}
      </ScrollView>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    marginBottom: 16,
  },
  scrollContent: {
    paddingHorizontal: 16,
    gap: 10,
  },
  tickerItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderRadius: 12,
    borderWidth: 1,
    minWidth: 140,
  },
  iconWrap: {
    width: 30,
    height: 30,
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
  },
  tickerContent: {
    flex: 1,
    gap: 2,
  },
  tickerName: {
    fontSize: 10,
    fontFamily: 'DM Sans',
    fontWeight: '500',
  },
  tickerPrice: {
    fontSize: 13,
    fontFamily: 'DM Sans',
    fontWeight: '700',
  },
  changeBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 2,
    paddingHorizontal: 6,
    paddingVertical: 3,
    borderRadius: 6,
  },
  changeText: {
    fontSize: 10,
    fontFamily: 'DM Sans',
    fontWeight: '700',
  },
});
