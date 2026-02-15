import React, { useEffect, useState, useRef } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TextInput, TouchableOpacity,
  KeyboardAvoidingView, Platform, ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useAuth } from '../../src/context/AuthContext';
import { useTheme } from '../../src/context/ThemeContext';
import { apiRequest } from '../../src/utils/api';

type Message = { id: string; role: string; content: string; created_at: string };

const QUICK_PROMPTS = [
  'How can I save more this month?',
  'Suggest investments for my risk profile',
  'Analyze my spending habits',
  'Tax saving tips for Indian salaried employees',
  'How to build an emergency fund?',
];

export default function InsightsScreen() {
  const { token } = useAuth();
  const { colors, isDark } = useTheme();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const scrollRef = useRef<ScrollView>(null);

  useEffect(() => {
    fetchHistory();
  }, [token]);

  const fetchHistory = async () => {
    if (!token) return;
    try {
      const data = await apiRequest('/ai/history', { token });
      setMessages(data);
    } catch (e) { console.error(e); }
    finally { setLoadingHistory(false); }
  };

  const sendMessage = async (text?: string) => {
    const msg = text || input.trim();
    if (!msg || sending) return;
    setInput('');
    setSending(true);

    // Optimistic user message
    const tempUserMsg: Message = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: msg,
      created_at: new Date().toISOString(),
    };
    setMessages(prev => [...prev, tempUserMsg]);
    setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 100);

    try {
      const response = await apiRequest('/ai/chat', {
        method: 'POST', token,
        body: { message: msg },
      });
      setMessages(prev => [
        ...prev.filter(m => m.id !== tempUserMsg.id),
        { ...tempUserMsg, id: `user-${Date.now()}` },
        response,
      ]);
    } catch (e: any) {
      setMessages(prev => [
        ...prev,
        { id: `err-${Date.now()}`, role: 'assistant', content: 'Sorry, I had trouble responding. Please try again.', created_at: new Date().toISOString() },
      ]);
    } finally {
      setSending(false);
      setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 200);
    }
  };

  return (
    <SafeAreaView style={[styles.safe, { backgroundColor: colors.background }]}>
      <View style={[styles.header, { borderBottomColor: colors.border }]}>
        <View style={[styles.aiIcon, { backgroundColor: isDark ? '#312E81' : '#E0E7FF' }]}>
          <MaterialCommunityIcons name="robot" size={22} color={colors.secondary} />
        </View>
        <View>
          <Text style={[styles.headerTitle, { color: colors.textPrimary }]}>Visor AI Advisor</Text>
          <Text style={[styles.headerSub, { color: colors.textSecondary }]}>Powered by GPT-5.2</Text>
        </View>
      </View>

      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.flex} keyboardVerticalOffset={90}>
        <ScrollView
          ref={scrollRef}
          style={styles.flex}
          contentContainerStyle={styles.chatContainer}
          onContentSizeChange={() => scrollRef.current?.scrollToEnd({ animated: false })}
        >
          {loadingHistory ? (
            <View style={styles.center}><ActivityIndicator size="large" color={colors.primary} /></View>
          ) : messages.length === 0 ? (
            <View style={styles.emptyState}>
              <View style={[styles.bigIcon, { backgroundColor: isDark ? '#312E81' : '#E0E7FF' }]}>
                <MaterialCommunityIcons name="robot-happy" size={48} color={colors.secondary} />
              </View>
              <Text style={[styles.emptyTitle, { color: colors.textPrimary }]}>Your AI Finance Advisor</Text>
              <Text style={[styles.emptySubtitle, { color: colors.textSecondary }]}>
                Ask me anything about your finances, investments, taxes, or savings strategies.
              </Text>
              <View style={styles.promptsContainer}>
                {QUICK_PROMPTS.map((p, i) => (
                  <TouchableOpacity
                    key={i}
                    testID={`quick-prompt-${i}`}
                    style={[styles.promptChip, { backgroundColor: colors.surface, borderColor: colors.border }]}
                    onPress={() => sendMessage(p)}
                  >
                    <MaterialCommunityIcons name="lightning-bolt" size={14} color={colors.primary} />
                    <Text style={[styles.promptText, { color: colors.textPrimary }]}>{p}</Text>
                  </TouchableOpacity>
                ))}
              </View>
            </View>
          ) : (
            messages.map((msg) => (
              <View
                key={msg.id}
                style={[
                  styles.bubble,
                  msg.role === 'user' ? styles.userBubble : styles.aiBubble,
                  {
                    backgroundColor: msg.role === 'user'
                      ? colors.primary
                      : isDark ? colors.surface : '#F1F5F9',
                    borderColor: msg.role === 'user' ? colors.primary : colors.border,
                  },
                ]}
              >
                {msg.role === 'assistant' && (
                  <View style={styles.aiHeader}>
                    <MaterialCommunityIcons name="robot" size={14} color={colors.secondary} />
                    <Text style={[styles.aiLabel, { color: colors.secondary }]}>Visor AI</Text>
                  </View>
                )}
                <Text style={[styles.bubbleText, {
                  color: msg.role === 'user' ? '#fff' : colors.textPrimary,
                }]}>
                  {msg.content}
                </Text>
              </View>
            ))
          )}
          {sending && (
            <View style={[styles.bubble, styles.aiBubble, { backgroundColor: isDark ? colors.surface : '#F1F5F9', borderColor: colors.border }]}>
              <View style={styles.typingRow}>
                <ActivityIndicator size="small" color={colors.secondary} />
                <Text style={[styles.typingText, { color: colors.textSecondary }]}>Thinking...</Text>
              </View>
            </View>
          )}
          <View style={{ height: 16 }} />
        </ScrollView>

        {/* Input */}
        <View style={[styles.inputBar, { backgroundColor: colors.surface, borderTopColor: colors.border }]}>
          <TextInput
            testID="chat-input"
            style={[styles.chatInput, { backgroundColor: colors.background, borderColor: colors.border, color: colors.textPrimary }]}
            value={input}
            onChangeText={setInput}
            placeholder="Ask about your finances..."
            placeholderTextColor={colors.textSecondary}
            multiline
            maxLength={500}
          />
          <TouchableOpacity
            testID="send-message-btn"
            style={[styles.sendBtn, { backgroundColor: input.trim() ? colors.primary : colors.border }]}
            onPress={() => sendMessage()}
            disabled={!input.trim() || sending}
          >
            <MaterialCommunityIcons name="send" size={20} color={input.trim() ? '#fff' : colors.textSecondary} />
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1 },
  flex: { flex: 1 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', paddingTop: 60 },
  header: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 20, paddingVertical: 16, borderBottomWidth: 1, gap: 12 },
  aiIcon: { width: 40, height: 40, borderRadius: 12, justifyContent: 'center', alignItems: 'center' },
  headerTitle: { fontSize: 18, fontWeight: '700' },
  headerSub: { fontSize: 12 },

  chatContainer: { paddingHorizontal: 16, paddingTop: 16, flexGrow: 1 },
  emptyState: { alignItems: 'center', paddingTop: 40, paddingHorizontal: 20 },
  bigIcon: { width: 80, height: 80, borderRadius: 24, justifyContent: 'center', alignItems: 'center', marginBottom: 16 },
  emptyTitle: { fontSize: 20, fontWeight: '700', marginBottom: 8 },
  emptySubtitle: { fontSize: 14, textAlign: 'center', lineHeight: 20, marginBottom: 24 },
  promptsContainer: { gap: 8, width: '100%' },
  promptChip: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingHorizontal: 16, paddingVertical: 14, borderRadius: 16, borderWidth: 1 },
  promptText: { fontSize: 14, flex: 1 },

  bubble: { maxWidth: '85%', padding: 14, borderRadius: 18, marginBottom: 10, borderWidth: 1 },
  userBubble: { alignSelf: 'flex-end', borderBottomRightRadius: 4 },
  aiBubble: { alignSelf: 'flex-start', borderBottomLeftRadius: 4 },
  aiHeader: { flexDirection: 'row', alignItems: 'center', gap: 4, marginBottom: 6 },
  aiLabel: { fontSize: 11, fontWeight: '700' },
  bubbleText: { fontSize: 14, lineHeight: 21 },
  typingRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  typingText: { fontSize: 13 },

  inputBar: { flexDirection: 'row', alignItems: 'flex-end', paddingHorizontal: 12, paddingVertical: 10, borderTopWidth: 1, gap: 8 },
  chatInput: { flex: 1, minHeight: 44, maxHeight: 100, borderRadius: 22, borderWidth: 1, paddingHorizontal: 16, paddingTop: 12, paddingBottom: 12, fontSize: 15 },
  sendBtn: { width: 44, height: 44, borderRadius: 22, justifyContent: 'center', alignItems: 'center' },
});
