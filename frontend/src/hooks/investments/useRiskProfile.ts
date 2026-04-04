import { useState } from 'react';
import { Alert } from 'react-native';
import { apiRequest } from '../../utils/api';

export function useRiskProfile(token: string | null, fetchData: () => void) {
  const [showRiskModal, setShowRiskModal] = useState(false);
  const [riskStep, setRiskStep] = useState(0);
  const [riskAnswers, setRiskAnswers] = useState<{question_id: number; value: number; category: string}[]>([]);
  const [showRiskResult, setShowRiskResult] = useState(false);

  const handleRiskAnswer = (question_id: number, value: number, category: string) => {
    const existing = riskAnswers.find(a => a.question_id === question_id);
    if (existing) {
      setRiskAnswers(riskAnswers.map(a => a.question_id === question_id ? { question_id, value, category } : a));
    } else {
      setRiskAnswers([...riskAnswers, { question_id, value, category }]);
    }
  };

  const handleSubmitRiskProfile = async (profile: string, score: number, breakdown: Record<string, number>) => {
    try {
      await apiRequest('/risk-profile', {
        token,
        method: 'POST',
        body: { profile, score, breakdown, answers: riskAnswers },
      });
      Alert.alert('Risk Profile Saved', `Your profile: ${profile}`);
      setShowRiskModal(false);
      fetchData();
    } catch (e: any) {
      Alert.alert('Error', e.message || 'Failed to save risk profile');
    }
  };

  const resetRiskAssessment = () => {
    setRiskStep(0);
    setRiskAnswers([]);
    setShowRiskResult(false);
  };

  return {
    showRiskModal,
    setShowRiskModal,
    riskStep,
    setRiskStep,
    riskAnswers,
    showRiskResult,
    setShowRiskResult,
    handleRiskAnswer,
    handleSubmitRiskProfile,
    resetRiskAssessment,
  };
}
