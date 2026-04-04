import { useState, useCallback, useRef } from 'react';
import { Alert } from 'react-native';
import * as DocumentPicker from 'expo-document-picker';
import { apiRequest } from '../../utils/api';

export function useHoldingsManager(token: string | null, fetchData: () => void) {
  const [showHoldingModal, setShowHoldingModal] = useState(false);
  const [showCasModal, setShowCasModal] = useState(false);
  const [holdingForm, setHoldingForm] = useState({
    name: '',
    ticker: '',
    isin: '',
    category: 'Stock',
    quantity: '',
    buy_price: '',
    buy_date: '',
  });
  const [casPassword, setCasPassword] = useState('');
  const [uploadingStatement, setUploadingStatement] = useState(false);
  const [refreshingPrices, setRefreshingPrices] = useState(false);
  const isPickingRef = useRef(false);

  const handleRefreshPrices = async () => {
    setRefreshingPrices(true);
    try {
      const resp = await apiRequest('/holdings/refresh-prices', { method: 'POST', token });
      if (resp?.updated > 0) {
        Alert.alert('Prices Updated', `Updated ${resp.updated} of ${resp.total} holdings with live prices.`);
        fetchData();
      } else {
        Alert.alert('No Updates', resp?.message || 'Prices are already up to date.');
      }
    } catch (e: any) {
      Alert.alert('Error', e.message || 'Failed to refresh prices');
    } finally {
      setRefreshingPrices(false);
    }
  };

  // Safely open document picker
  const safePickDocument = async (options: Parameters<typeof DocumentPicker.getDocumentAsync>[0]) => {
    try {
      return await DocumentPicker.getDocumentAsync(options);
    } catch (e: any) {
      const msg: string = e?.message || '';
      if (msg.toLowerCase().includes('picking in progress') || msg.toLowerCase().includes('another picker')) {
        await new Promise(r => setTimeout(r, 800));
        return await DocumentPicker.getDocumentAsync(options);
      }
      throw e;
    }
  };

  const handleStatementUpload = async (type: 'stock_statement' | 'mf_statement' | 'ecas') => {
    if (type === 'ecas') {
      setShowCasModal(true);
      return;
    }
    if (isPickingRef.current) return;
    isPickingRef.current = true;
    try {
      const result = await safePickDocument({
        type: ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/vnd.ms-excel'],
        copyToCacheDirectory: true,
      });
      if (result.canceled || !result.assets?.length) return;
      const file = result.assets[0];
      setUploadingStatement(true);
      const formData = new FormData();
      formData.append('file', { uri: file.uri, name: file.name, type: file.mimeType || 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' } as any);
      formData.append('statement_type', type);
      const resp = await apiRequest('/upload-statement', { token, method: 'POST', body: formData, isFormData: true });
      setUploadingStatement(false);
      if (resp?.status === 'success') {
        const sipMsg = resp.sip_suggestions_created > 0 ? `\n${resp.sip_suggestions_created} SIP suggestion(s) added for your review.` : '';
        Alert.alert('Import Successful', `${resp.saved} holdings imported, ${resp.duplicates} updated.\nSource: ${resp.metadata?.source || 'Unknown'}${sipMsg}`);
        fetchData();
      } else if (resp?.status === 'no_holdings') {
        Alert.alert('No Holdings Found', resp.message || 'Please check the file format.');
      } else {
        Alert.alert('Import Failed', resp?.detail || resp?.message || 'Unknown error');
      }
    } catch (e: any) {
      setUploadingStatement(false);
      Alert.alert('Upload Error', e.message || 'Failed to upload statement');
    } finally {
      isPickingRef.current = false;
    }
  };

  const handleClearHoldings = () => {
    Alert.alert('Clear All Holdings?', 'This will permanently delete all your holdings and cannot be undone.', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Clear All',
        style: 'destructive',
        onPress: async () => {
          try {
            await apiRequest('/holdings/clear', { method: 'DELETE', token });
            Alert.alert('Success', 'All holdings cleared');
            fetchData();
          } catch (e: any) {
            Alert.alert('Error', e.message || 'Failed to clear holdings');
          }
        },
      },
    ]);
  };

  return {
    showHoldingModal,
    setShowHoldingModal,
    showCasModal,
    setShowCasModal,
    holdingForm,
    setHoldingForm,
    casPassword,
    setCasPassword,
    uploadingStatement,
    setUploadingStatement,
    refreshingPrices,
    handleRefreshPrices,
    handleStatementUpload,
    handleClearHoldings,
  };
}
