import React, { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ActivityIndicator, Alert, Platform } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import * as DocumentPicker from 'expo-document-picker';
import { apiRequest, API_URL } from '../../utils/api';
import { formatINRShort } from '../../utils/formatters';
import { Accent } from '../../utils/theme';

interface TaxDocumentUploadProps {
  token: string;
  colors: any;
  isDark: boolean;
  onUploadComplete?: () => void;
}

type DocumentType = 'form16' | 'ais' | 'form26as' | 'fd_certificate';

interface UploadOption {
  id: DocumentType;
  title: string;
  description: string;
  icon: string;
  acceptedTypes: string[];
  endpoint: string;
}

const UPLOAD_OPTIONS: UploadOption[] = [
  {
    id: 'form16',
    title: 'Form 16',
    description: 'Upload salary certificate from employer',
    icon: 'file-document-outline',
    acceptedTypes: ['application/pdf'],
    endpoint: '/tax/upload/form16',
  },
  {
    id: 'ais',
    title: 'AIS / Form 26AS',
    description: 'Annual Information Statement or TDS statement',
    icon: 'file-chart-outline',
    acceptedTypes: ['application/pdf', 'application/json'],
    endpoint: '/tax/upload/ais',
  },
  {
    id: 'fd_certificate',
    title: 'FD Interest Certificate',
    description: 'Fixed deposit interest certificate from bank',
    icon: 'bank-outline',
    acceptedTypes: ['application/pdf'],
    endpoint: '/tax/upload/fd-certificate',
  },
];

export const TaxDocumentUpload: React.FC<TaxDocumentUploadProps> = ({
  token,
  colors,
  isDark,
  onUploadComplete,
}) => {
  const [uploading, setUploading] = useState<DocumentType | null>(null);
  const [lastResult, setLastResult] = useState<any>(null);
  const [expanded, setExpanded] = useState(false);

  const handleUpload = async (option: UploadOption) => {
    try {
      // Pick document
      const result = await DocumentPicker.getDocumentAsync({
        type: option.acceptedTypes,
        copyToCacheDirectory: true,
      });

      if (result.canceled || !result.assets?.length) {
        return;
      }

      const file = result.assets[0];
      setUploading(option.id);
      setLastResult(null);

      // Create form data
      const formData = new FormData();
      formData.append('file', {
        uri: file.uri,
        name: file.name,
        type: file.mimeType || 'application/pdf',
      } as any);

      // Upload
      const response = await fetch(`${API_URL}${option.endpoint}`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Upload failed');
      }

      const data = await response.json();
      setLastResult({ type: option.id, data });
      
      if (onUploadComplete) {
        onUploadComplete();
      }

      Alert.alert(
        'Upload Successful',
        option.id === 'form16'
          ? `Parsed Form 16: ${data.employer_info?.employer_name || 'Unknown Employer'}\nGross Salary: ${formatINRShort(data.summary?.gross_salary || 0)}\nTDS: ${formatINRShort(data.tax_computation?.tds_deducted || 0)}`
          : option.id === 'fd_certificate'
          ? `Extracted ${data.fd_count} FD(s)\nTotal Interest: ${formatINRShort(data.summary?.total_interest || 0)}\nTDS: ${formatINRShort(data.summary?.total_tds || 0)}`
          : `Processed ${option.title}\nTDS entries: ${data.tds_entries_count || 0}\nTotal TDS: ${formatINRShort(data.summary?.total_tds || 0)}`
      );
    } catch (error: any) {
      Alert.alert('Upload Failed', error.message || 'Could not process the document');
    } finally {
      setUploading(null);
    }
  };

  return (
    <View style={{ marginBottom: 16 }}>
      {/* Header */}
      <TouchableOpacity
        data-testid="tax-documents-header"
        style={[styles.header, {
          backgroundColor: isDark ? 'rgba(10,10,11,0.85)' : 'rgba(255,255,255,0.9)',
          borderColor: isDark ? 'rgba(59,130,246,0.15)' : 'rgba(59,130,246,0.1)',
        }]}
        onPress={() => setExpanded(!expanded)}
        activeOpacity={0.7}
      >
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
          <View style={[styles.iconWrap, { backgroundColor: 'rgba(59,130,246,0.12)' }]}>
            <MaterialCommunityIcons name="file-upload-outline" size={18} color="#3B82F6" />
          </View>
          <View>
            <Text style={[styles.title, { color: colors.textPrimary }]}>
              Upload Tax Documents
            </Text>
            <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
              Form 16, AIS, 26AS, FD Certificates
            </Text>
          </View>
        </View>
        <MaterialCommunityIcons 
          name={expanded ? 'chevron-up' : 'chevron-down'} 
          size={24} 
          color={colors.textSecondary} 
        />
      </TouchableOpacity>

      {/* Expanded Upload Options */}
      {expanded && (
        <View style={[styles.optionsContainer, {
          backgroundColor: isDark ? 'rgba(10,10,11,0.85)' : 'rgba(255,255,255,0.9)',
          borderColor: isDark ? 'rgba(59,130,246,0.1)' : 'rgba(59,130,246,0.06)',
        }]}>
          {UPLOAD_OPTIONS.map((option) => (
            <TouchableOpacity
              key={option.id}
              data-testid={`upload-${option.id}-btn`}
              style={[styles.uploadOption, {
                backgroundColor: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.02)',
                borderColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)',
              }]}
              onPress={() => handleUpload(option)}
              disabled={uploading !== null}
              activeOpacity={0.7}
            >
              <View style={[styles.optionIcon, { backgroundColor: 'rgba(59,130,246,0.08)' }]}>
                {uploading === option.id ? (
                  <ActivityIndicator size="small" color="#3B82F6" />
                ) : (
                  <MaterialCommunityIcons name={option.icon as any} size={20} color="#3B82F6" />
                )}
              </View>
              <View style={{ flex: 1 }}>
                <Text style={[styles.optionTitle, { color: colors.textPrimary }]}>
                  {option.title}
                </Text>
                <Text style={[styles.optionDesc, { color: colors.textSecondary }]}>
                  {option.description}
                </Text>
              </View>
              <MaterialCommunityIcons name="upload" size={18} color={colors.textSecondary} />
            </TouchableOpacity>
          ))}

          {/* Last Upload Result */}
          {lastResult && (
            <View style={[styles.resultBanner, {
              backgroundColor: 'rgba(16,185,129,0.08)',
              borderColor: 'rgba(16,185,129,0.15)',
            }]}>
              <MaterialCommunityIcons name="check-circle" size={16} color={Accent.emerald} />
              <Text style={[styles.resultText, { color: Accent.emerald }]}>
                Last upload: {lastResult.type === 'form16' ? 'Form 16' : lastResult.type === 'fd_certificate' ? 'FD Certificate' : 'AIS/26AS'} processed successfully
              </Text>
            </View>
          )}

          {/* Help Text */}
          <Text style={[styles.helpText, { color: colors.textSecondary }]}>
            Supported formats: PDF, JSON (for AIS). Documents are parsed automatically to extract tax-relevant information.
          </Text>
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 14,
    borderRadius: 14,
    borderWidth: 1,
  },
  iconWrap: {
    width: 40,
    height: 40,
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
  },
  title: {
    fontSize: 14,
    fontFamily: 'DM Sans',
    fontWeight: '700',
  },
  subtitle: {
    fontSize: 11,
    fontFamily: 'DM Sans',
    marginTop: 2,
  },
  optionsContainer: {
    marginTop: 8,
    padding: 14,
    borderRadius: 14,
    borderWidth: 1,
    gap: 10,
  },
  uploadOption: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    borderRadius: 12,
    borderWidth: 1,
    gap: 12,
  },
  optionIcon: {
    width: 44,
    height: 44,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
  },
  optionTitle: {
    fontSize: 13,
    fontFamily: 'DM Sans',
    fontWeight: '600',
  },
  optionDesc: {
    fontSize: 11,
    fontFamily: 'DM Sans',
    marginTop: 2,
  },
  resultBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    padding: 10,
    borderRadius: 10,
    borderWidth: 1,
  },
  resultText: {
    fontSize: 12,
    fontFamily: 'DM Sans',
    fontWeight: '500',
    flex: 1,
  },
  helpText: {
    fontSize: 10,
    fontFamily: 'DM Sans',
    fontStyle: 'italic',
    textAlign: 'center',
    marginTop: 4,
  },
});
