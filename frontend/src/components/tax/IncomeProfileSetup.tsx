import React, { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ActivityIndicator, Alert } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { apiRequest } from '../../utils/api';
import { Accent } from '../../utils/theme';

const INCOME_TYPES = [
  { id: 'salaried', label: 'Salaried', icon: 'briefcase-outline', desc: 'Fixed monthly salary' },
  { id: 'freelancer', label: 'Freelancer', icon: 'laptop', desc: 'Consulting/gig income' },
  { id: 'business', label: 'Business', icon: 'store-outline', desc: 'Own business/trading' },
  { id: 'investor', label: 'Investor', icon: 'chart-line', desc: 'Stocks, F&O, MF gains' },
  { id: 'rental', label: 'Rental', icon: 'home-outline', desc: 'Rental property income' },
];

interface Props {
  token: string;
  colors: any;
  isDark: boolean;
  onSaved: (profile: any) => void;
}

export function IncomeProfileSetup({ token, colors, isDark, onSaved }: Props) {
  const [selected, setSelected] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);

  const toggle = (id: string) => {
    setSelected(prev =>
      prev.includes(id) ? prev.filter(s => s !== id) : [...prev, id]
    );
  };

  const save = async () => {
    if (selected.length === 0) {
      Alert.alert('Select at least one income type');
      return;
    }
    setSaving(true);
    try {
      const result = await apiRequest('/tax/income-profile', {
        method: 'POST', token,
        body: {
          income_types: selected,
          primary_income_type: selected[0],
          fy: '2025-26',
        },
      });
      onSaved(result.profile);
    } catch (e: any) {
      Alert.alert('Error', e.message || 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  return (
    <View
      data-testid="income-profile-setup"
      style={[styles.card, {
        backgroundColor: isDark ? 'rgba(245,158,11,0.06)' : 'rgba(245,158,11,0.04)',
        borderColor: isDark ? 'rgba(245,158,11,0.25)' : 'rgba(245,158,11,0.18)',
      }]}
    >
      <View style={styles.header}>
        <MaterialCommunityIcons name="account-cog-outline" size={18} color="#F59E0B" />
        <View style={{ flex: 1, marginLeft: 8 }}>
          <Text style={[styles.title, { color: colors.textPrimary }]}>Set Up Your Tax Profile</Text>
          <Text style={[styles.subtitle, { color: colors.textSecondary }]}>Select all income types that apply this FY</Text>
        </View>
      </View>

      <View style={styles.chips}>
        {INCOME_TYPES.map(type => {
          const isSelected = selected.includes(type.id);
          return (
            <TouchableOpacity
              key={type.id}
              data-testid={`income-type-${type.id}`}
              style={[styles.chip, {
                backgroundColor: isSelected
                  ? (isDark ? 'rgba(245,158,11,0.2)' : 'rgba(245,158,11,0.12)')
                  : (isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.04)'),
                borderColor: isSelected ? '#F59E0B' : (isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)'),
              }]}
              onPress={() => toggle(type.id)}
              activeOpacity={0.75}
            >
              <MaterialCommunityIcons
                name={type.icon as any}
                size={16}
                color={isSelected ? '#F59E0B' : colors.textSecondary}
              />
              <View style={{ marginLeft: 6 }}>
                <Text style={[styles.chipLabel, { color: isSelected ? '#F59E0B' : colors.textPrimary }]}>
                  {type.label}
                </Text>
                <Text style={[styles.chipDesc, { color: colors.textSecondary }]}>{type.desc}</Text>
              </View>
            </TouchableOpacity>
          );
        })}
      </View>

      <TouchableOpacity
        data-testid="save-income-profile-btn"
        style={[styles.saveBtn, { opacity: selected.length === 0 ? 0.5 : 1 }]}
        onPress={save}
        disabled={saving || selected.length === 0}
        activeOpacity={0.8}
      >
        {saving
          ? <ActivityIndicator size="small" color="#fff" />
          : <Text style={styles.saveBtnText}>Confirm Profile</Text>
        }
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  card: { borderRadius: 14, padding: 14, borderWidth: 1, marginBottom: 14 },
  header: { flexDirection: 'row', alignItems: 'flex-start', marginBottom: 12 },
  title: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '700' },
  subtitle: { fontSize: 11, fontFamily: 'DM Sans', marginTop: 1 },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 12 },
  chip: {
    flexDirection: 'row', alignItems: 'center',
    paddingHorizontal: 10, paddingVertical: 8, borderRadius: 10, borderWidth: 1,
    minWidth: '45%', flex: 0,
  },
  chipLabel: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '700' },
  chipDesc: { fontSize: 10, fontFamily: 'DM Sans', marginTop: 1 },
  saveBtn: {
    backgroundColor: '#F59E0B', borderRadius: 10, paddingVertical: 10,
    alignItems: 'center', justifyContent: 'center',
  },
  saveBtnText: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '700', color: '#fff' },
});
