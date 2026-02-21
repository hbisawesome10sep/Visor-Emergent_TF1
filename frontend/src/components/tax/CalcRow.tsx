import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { formatINR } from '../../utils/formatters';

interface CalcRowProps {
  label: string;
  value: number;
  colors: any;
  bold?: boolean;
  highlight?: string;
  sublabel?: string;
}

export const CalcRow: React.FC<CalcRowProps> = ({ label, value, colors, bold, highlight, sublabel }) => {
  return (
    <View style={styles.calcRow}>
      <View style={{ flex: 1 }}>
        <Text style={[styles.calcLabel, { color: colors.textSecondary, fontWeight: bold ? '600' : '400' }]}>
          {label}
        </Text>
        {sublabel && (
          <Text style={[styles.calcSublabel, { color: colors.textSecondary }]}>{sublabel}</Text>
        )}
      </View>
      <Text style={[
        styles.calcValue,
        { color: highlight || (bold ? colors.textPrimary : colors.textSecondary), fontWeight: bold ? '700' : '500' }
      ]}>
        {value < 0 ? `(${formatINR(Math.abs(value))})` : formatINR(value)}
      </Text>
    </View>
  );
};

const styles = StyleSheet.create({
  calcRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
  },
  calcLabel: {
    fontSize: 13,
    fontFamily: 'DM Sans',
  },
  calcSublabel: {
    fontSize: 10,
    fontFamily: 'DM Sans',
    marginTop: 2,
  },
  calcValue: {
    fontSize: 13,
    fontFamily: 'DM Sans',
  },
});
