import React, { useState } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, Animated,
  Linking, TouchableWithoutFeedback,
} from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';

type UploadType = 'stock_statement' | 'mf_statement' | 'ecas';

interface Props {
  colors: any;
  isDark: boolean;
  token: string;
  onSelect?: (type: UploadType) => void; // kept for compat but not used for file picking
}

const OPTIONS: { key: UploadType; label: string; icon: string; desc: string; color: string }[] = [
  { key: 'stock_statement', label: 'Stock Holdings',       icon: 'chart-line',       desc: 'Groww / Zerodha stock XLSX',     color: '#F97316' },
  { key: 'mf_statement',   label: 'Mutual Fund Holdings',  icon: 'chart-arc',        desc: 'Groww / Zerodha MF XLSX',        color: '#6366F1' },
  { key: 'ecas',           label: 'eCAS Statement',        icon: 'file-certificate', desc: 'CAMS/KFintech consolidated PDF', color: '#10B981' },
];

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL || '';

export const UploadDropdown: React.FC<Props> = ({ colors, isDark, token }) => {
  const [open, setOpen] = useState(false);
  const anim = React.useRef(new Animated.Value(0)).current;

  const show = () => {
    setOpen(true);
    Animated.spring(anim, { toValue: 1, useNativeDriver: true, tension: 300, friction: 20 }).start();
  };

  const hide = () => {
    Animated.timing(anim, { toValue: 0, duration: 150, useNativeDriver: true }).start(() => setOpen(false));
  };

  const handleOptionPress = (key: UploadType) => {
    hide();
    // Open Safari web upload page — completely bypasses iOS native document picker
    const url = `${BACKEND_URL}/api/upload-page?token=${encodeURIComponent(token)}&type=${key}`;
    setTimeout(() => Linking.openURL(url), 200);
  };

  return (
    <View style={{ zIndex: 100 }}>
      <TouchableOpacity
        data-testid="upload-statement-dropdown"
        style={[s.trigger, {
          backgroundColor: isDark ? 'rgba(249,115,22,0.12)' : 'rgba(249,115,22,0.06)',
          borderColor: isDark ? 'rgba(249,115,22,0.3)' : 'rgba(249,115,22,0.2)',
        }]}
        onPress={open ? hide : show}
        activeOpacity={0.8}
      >
        <MaterialCommunityIcons name="file-upload-outline" size={18} color="#F97316" />
        <Text style={s.triggerText}>Import Statement</Text>
        <MaterialCommunityIcons name={open ? 'chevron-up' : 'chevron-down'} size={16} color="#F97316" />
      </TouchableOpacity>

      {open && (
        <TouchableWithoutFeedback onPress={hide}>
          <View style={s.backdrop} />
        </TouchableWithoutFeedback>
      )}

      {open && (
        <Animated.View
          style={[s.sheet, {
            backgroundColor: isDark ? '#1C1C1E' : '#FFFFFF',
            borderColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)',
            opacity: anim,
            transform: [{ translateY: anim.interpolate({ inputRange: [0, 1], outputRange: [-8, 0] }) }],
          }]}
        >
          <Text style={[s.sheetTitle, { color: colors.textPrimary }]}>Import Statement</Text>
          <Text style={[s.sheetDesc, { color: colors.textSecondary }]}>
            Opens in Safari — works on iOS &amp; Android
          </Text>

          {OPTIONS.map((opt) => (
            <TouchableOpacity
              key={opt.key}
              data-testid={`upload-opt-${opt.key}`}
              style={[s.optRow, {
                backgroundColor: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.02)',
                borderColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)',
              }]}
              onPress={() => handleOptionPress(opt.key)}
              activeOpacity={0.7}
            >
              <View style={[s.optIcon, { backgroundColor: `${opt.color}20` }]}>
                <MaterialCommunityIcons name={opt.icon as any} size={20} color={opt.color} />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={[s.optLabel, { color: colors.textPrimary }]}>{opt.label}</Text>
                <Text style={[s.optDesc, { color: colors.textSecondary }]}>{opt.desc}</Text>
              </View>
              <MaterialCommunityIcons name="open-in-new" size={14} color={colors.textSecondary} />
            </TouchableOpacity>
          ))}
        </Animated.View>
      )}
    </View>
  );
};

const s = StyleSheet.create({
  trigger: {
    flexDirection: 'row', alignItems: 'center', gap: 8,
    paddingHorizontal: 14, paddingVertical: 10,
    borderRadius: 12, borderWidth: 1,
  },
  triggerText: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '700', color: '#F97316' },
  backdrop: {
    position: 'absolute', top: 46, left: -1000, right: -1000, bottom: -2000,
    zIndex: 98,
  },
  sheet: {
    position: 'absolute', top: 48, left: 0, right: 0,
    borderRadius: 16, borderWidth: 1,
    padding: 14, zIndex: 99,
    shadowColor: '#000', shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.18, shadowRadius: 12, elevation: 10,
  },
  sheetTitle: { fontSize: 15, fontFamily: 'DM Sans', fontWeight: '700', marginBottom: 2 },
  sheetDesc: { fontSize: 12, fontFamily: 'DM Sans', marginBottom: 12 },
  optRow: {
    flexDirection: 'row', alignItems: 'center', gap: 12,
    padding: 12, borderRadius: 12, borderWidth: 1, marginBottom: 8,
  },
  optIcon: { width: 38, height: 38, borderRadius: 10, alignItems: 'center', justifyContent: 'center' },
  optLabel: { fontSize: 14, fontFamily: 'DM Sans', fontWeight: '700' },
  optDesc: { fontSize: 11, fontFamily: 'DM Sans', marginTop: 1 },
});
