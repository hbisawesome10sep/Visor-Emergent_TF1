import React, { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Modal } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Accent } from '../../utils/theme';

type UploadType = 'stock_statement' | 'mf_statement' | 'ecas';

interface Props {
  colors: any;
  isDark: boolean;
  onSelect: (type: UploadType) => void;
}

const OPTIONS: { key: UploadType; label: string; icon: string; desc: string; color: string }[] = [
  { key: 'stock_statement', label: 'Stock Holdings', icon: 'chart-line', desc: 'Groww / Zerodha stock statement', color: '#F97316' },
  { key: 'mf_statement', label: 'Mutual Fund Holdings', icon: 'chart-arc', desc: 'Groww / Zerodha MF statement', color: '#6366F1' },
  { key: 'ecas', label: 'eCAS Statement', icon: 'file-certificate', desc: 'CAMS/KFintech consolidated PDF', color: '#10B981' },
];

export const UploadDropdown: React.FC<Props> = ({ colors, isDark, onSelect }) => {
  const [open, setOpen] = useState(false);

  return (
    <>
      <TouchableOpacity
        data-testid="upload-statement-dropdown"
        style={[s.trigger, {
          backgroundColor: isDark ? 'rgba(249,115,22,0.12)' : 'rgba(249,115,22,0.06)',
          borderColor: isDark ? 'rgba(249,115,22,0.3)' : 'rgba(249,115,22,0.2)',
        }]}
        onPress={() => setOpen(true)}
      >
        <MaterialCommunityIcons name="file-upload-outline" size={18} color="#F97316" />
        <Text style={s.triggerText}>Import Statement</Text>
        <MaterialCommunityIcons name="chevron-down" size={16} color="#F97316" />
      </TouchableOpacity>

      <Modal visible={open} transparent animationType="fade" onRequestClose={() => setOpen(false)}>
        <TouchableOpacity style={s.overlay} activeOpacity={1} onPress={() => setOpen(false)}>
          <View style={[s.sheet, {
            backgroundColor: isDark ? '#141416' : '#FFFFFF',
            borderColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)',
          }]}>
            <View style={s.sheetHandle} />
            <Text style={[s.sheetTitle, { color: colors.textPrimary }]}>Import Statement</Text>
            <Text style={[s.sheetDesc, { color: colors.textSecondary }]}>
              Select the type of statement to upload
            </Text>
            {OPTIONS.map((opt) => (
              <TouchableOpacity
                key={opt.key}
                data-testid={`upload-opt-${opt.key}`}
                style={[s.optRow, {
                  backgroundColor: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.02)',
                  borderColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)',
                }]}
                onPress={() => { setOpen(false); onSelect(opt.key); }}
              >
                <View style={[s.optIcon, { backgroundColor: `${opt.color}18` }]}>
                  <MaterialCommunityIcons name={opt.icon as any} size={22} color={opt.color} />
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={[s.optLabel, { color: colors.textPrimary }]}>{opt.label}</Text>
                  <Text style={[s.optDesc, { color: colors.textSecondary }]}>{opt.desc}</Text>
                </View>
                <MaterialCommunityIcons name="chevron-right" size={18} color={colors.textSecondary} />
              </TouchableOpacity>
            ))}
          </View>
        </TouchableOpacity>
      </Modal>
    </>
  );
};

const s = StyleSheet.create({
  trigger: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingHorizontal: 14, paddingVertical: 10, borderRadius: 12, borderWidth: 1 },
  triggerText: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '700', color: '#F97316' },
  overlay: { flex: 1, justifyContent: 'flex-end', backgroundColor: 'rgba(0,0,0,0.6)' },
  sheet: { borderTopLeftRadius: 24, borderTopRightRadius: 24, borderWidth: 1, borderBottomWidth: 0, padding: 20, paddingBottom: 36 },
  sheetHandle: { width: 36, height: 4, borderRadius: 2, backgroundColor: 'rgba(128,128,128,0.3)', alignSelf: 'center', marginBottom: 16 },
  sheetTitle: { fontSize: 18, fontFamily: 'DM Sans', fontWeight: '700', marginBottom: 4 },
  sheetDesc: { fontSize: 13, fontFamily: 'DM Sans', marginBottom: 20 },
  optRow: { flexDirection: 'row', alignItems: 'center', gap: 14, padding: 14, borderRadius: 14, borderWidth: 1, marginBottom: 10 },
  optIcon: { width: 42, height: 42, borderRadius: 12, alignItems: 'center', justifyContent: 'center' },
  optLabel: { fontSize: 15, fontFamily: 'DM Sans', fontWeight: '700' },
  optDesc: { fontSize: 12, fontFamily: 'DM Sans', marginTop: 2 },
});
