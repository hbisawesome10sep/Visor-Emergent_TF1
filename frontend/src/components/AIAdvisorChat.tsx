import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, Modal, TextInput,
  ScrollView, KeyboardAvoidingView, Platform, ActivityIndicator,
  Dimensions, Animated, Alert, Pressable,
} from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { apiRequest } from '../utils/api';
import { useScreenContext } from '../context/ScreenContext';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

type Message = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  calculator_result?: Record<string, any>;
  created_at: string;
};

type Props = {
  token: string | null;
  colors: any;
  isDark: boolean;
};

const QUICK_PROMPT_CATEGORIES = [
  {
    title: 'Portfolio',
    prompts: [
      { icon: 'chart-line', label: 'Review my portfolio', prompt: 'Mera portfolio kaisa chal raha hai? Koi changes karne chahiye?' },
      { icon: 'scale-balance', label: 'Asset Allocation', prompt: 'Meri asset allocation theek hai ya rebalance karna chahiye?' },
    ],
  },
  {
    title: 'Tax & Savings',
    prompts: [
      { icon: 'file-document-outline', label: 'Tax Planning', prompt: 'Tax bachane ke liye kya kya kar sakta hoon? 80C, 80D sab batao.' },
      { icon: 'calculator-variant', label: 'Old vs New Regime', prompt: 'Mere liye Old Tax Regime better hai ya New? Compare karo.' },
    ],
  },
  {
    title: 'Investments',
    prompts: [
      { icon: 'trending-up', label: 'SIP Calculator', prompt: '₹10,000 monthly SIP mein 15 saal baad kitna milega at 12% return?' },
      { icon: 'home-outline', label: 'Home Loan EMI', prompt: '₹50 lakh home loan ka EMI batao at 8.5% for 20 years' },
    ],
  },
  {
    title: 'Market & News',
    prompts: [
      { icon: 'newspaper-variant-outline', label: 'Market Update', prompt: 'Aaj market mein kya chal raha hai? Latest news batao.' },
      { icon: 'fire', label: 'FIRE Number', prompt: 'Mere expenses ke hisaab se mera FIRE number kya hoga?' },
    ],
  },
];

// Render rich text with basic markdown support
function RichText({ content, color }: { content: string; color: string }) {
  const parts = content.split(/(\*\*.*?\*\*|\*.*?\*|`.*?`)/g);
  return (
    <Text style={[styles.messageText, { color }]}>
      {parts.map((part, i) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          return <Text key={i} style={{ fontWeight: '700' }}>{part.slice(2, -2)}</Text>;
        }
        if (part.startsWith('*') && part.endsWith('*')) {
          return <Text key={i} style={{ fontStyle: 'italic' }}>{part.slice(1, -1)}</Text>;
        }
        if (part.startsWith('`') && part.endsWith('`')) {
          return <Text key={i} style={{ fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace', fontSize: 13 }}>{part.slice(1, -1)}</Text>;
        }
        return <Text key={i}>{part}</Text>;
      })}
    </Text>
  );
}

export default function AIAdvisorChat({ token, colors, isDark }: Props) {
  const { getScreenContext } = useScreenContext();
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const scrollViewRef = useRef<ScrollView>(null);
  const pulseAnim = useRef(new Animated.Value(1)).current;
  const glowAnim = useRef(new Animated.Value(0)).current;

  const c = colors || {
    background: isDark ? '#0A0A0B' : '#FFFFFF',
    textPrimary: isDark ? '#FFFFFF' : '#111827',
    textSecondary: isDark ? '#9CA3AF' : '#6B7280',
    primary: '#10B981',
    card: isDark ? '#1F2937' : '#F9FAFB',
  };

  // Gentle breathing animation for FAB
  useEffect(() => {
    const pulse = Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, { toValue: 1.08, duration: 1500, useNativeDriver: true }),
        Animated.timing(pulseAnim, { toValue: 1, duration: 1500, useNativeDriver: true }),
      ])
    );
    pulse.start();
    return () => pulse.stop();
  }, []);

  // Glow animation when loading
  useEffect(() => {
    if (isLoading) {
      const glow = Animated.loop(
        Animated.sequence([
          Animated.timing(glowAnim, { toValue: 1, duration: 800, useNativeDriver: false }),
          Animated.timing(glowAnim, { toValue: 0, duration: 800, useNativeDriver: false }),
        ])
      );
      glow.start();
      return () => glow.stop();
    } else {
      glowAnim.setValue(0);
    }
  }, [isLoading]);

  useEffect(() => {
    if (token && isOpen) loadHistory();
  }, [token, isOpen]);

  const loadHistory = async () => {
    if (!token) return;
    setIsLoadingHistory(true);
    try {
      const history = await apiRequest('/visor-ai/history', { token });
      setMessages(history.map((h: any) => ({
        id: h.id, role: h.role, content: h.content, created_at: h.created_at,
      })));
    } catch {
      // Try legacy endpoint as fallback
      try {
        const history = await apiRequest('/ai/history', { token });
        setMessages(history.map((h: any) => ({
          id: h.id, role: h.role, content: h.content, created_at: h.created_at,
        })));
      } catch { /* ignore */ }
    } finally {
      setIsLoadingHistory(false);
    }
  };

  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || !token || isLoading) return;
    const trimmed = text.trim();

    const userMessage: Message = {
      id: Date.now().toString(), role: 'user', content: trimmed,
      created_at: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMessage]);
    setInputText('');
    setIsLoading(true);
    setTimeout(() => scrollViewRef.current?.scrollToEnd({ animated: true }), 100);

    try {
      const screenContext = getScreenContext();
      const response = await apiRequest('/visor-ai/chat', {
        method: 'POST', token,
        body: { message: trimmed, screen_context: screenContext },
      });

      if (response.user_msg_id) {
        setMessages(prev => prev.map(m =>
          m.id === userMessage.id ? { ...m, id: response.user_msg_id } : m
        ));
      }

      setMessages(prev => [...prev, {
        id: response.id || (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.content,
        calculator_result: response.calculator_result,
        created_at: new Date().toISOString(),
      }]);
      setTimeout(() => scrollViewRef.current?.scrollToEnd({ animated: true }), 150);
    } catch (e: any) {
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(), role: 'assistant',
        content: `Connection mein issue aa raha hai. Ek baar phir try kar. (${e.message || 'Error'})`,
        created_at: new Date().toISOString(),
      }]);
    } finally {
      setIsLoading(false);
    }
  }, [token, isLoading, getScreenContext]);

  const clearChat = async () => {
    if (!token) return;
    Alert.alert('Clear Chat', 'Poora chat history delete ho jayega. Sure ho?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Delete', style: 'destructive', onPress: async () => {
        try {
          await apiRequest('/visor-ai/history', { method: 'DELETE', token });
          setMessages([]);
        } catch { /* ignore */ }
      }},
    ]);
  };

  const deleteMessage = (msgId: string) => {
    Alert.alert('Delete Message', 'Ye message delete karna hai?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Delete', style: 'destructive', onPress: async () => {
        try {
          await apiRequest(`/visor-ai/message/${msgId}`, { method: 'DELETE', token });
          setMessages(prev => prev.filter(m => m.id !== msgId));
        } catch { /* ignore */ }
      }},
    ]);
  };

  const ACCENT = '#10B981';
  const ACCENT_BG = isDark ? 'rgba(16,185,129,0.12)' : 'rgba(16,185,129,0.08)';

  return (
    <>
      {/* Floating Action Button — Friendly coin icon */}
      <Animated.View style={[styles.floatingBtn, { transform: [{ scale: pulseAnim }] }]}
        data-testid="visor-ai-fab"
      >
        <TouchableOpacity
          style={styles.aiButton}
          onPress={() => setIsOpen(true)}
          activeOpacity={0.85}
          data-testid="visor-ai-open-btn"
        >
          <LinearGradient
            colors={['#10B981', '#059669']}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 1 }}
            style={styles.aiButtonGradient}
          >
            <MaterialCommunityIcons name="shield-star" size={26} color="#fff" />
          </LinearGradient>
        </TouchableOpacity>
        <View style={styles.aiBadge}>
          <Text style={styles.aiBadgeText}>V</Text>
        </View>
      </Animated.View>

      {/* Chat Modal */}
      <Modal visible={isOpen} animationType="slide" transparent={false} onRequestClose={() => setIsOpen(false)}>
        <View style={[styles.container, { backgroundColor: c.background }]}>
          {/* Header */}
          <View style={[styles.header, {
            backgroundColor: isDark ? 'rgba(10,10,11,0.98)' : 'rgba(255,255,255,0.98)',
            borderBottomColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
          }]}>
            <View style={styles.headerLeft}>
              <LinearGradient colors={['#10B981', '#059669']} style={styles.headerIcon}>
                <MaterialCommunityIcons name="shield-star" size={20} color="#fff" />
              </LinearGradient>
              <View>
                <Text style={[styles.headerTitle, { color: c.textPrimary }]} data-testid="visor-ai-title">Visor</Text>
                <Text style={[styles.headerSub, { color: c.textSecondary }]}>Your Finance Companion</Text>
              </View>
            </View>
            <View style={styles.headerRight}>
              <TouchableOpacity style={[styles.hBtn, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.04)' }]}
                onPress={clearChat} data-testid="visor-ai-clear-btn">
                <MaterialCommunityIcons name="broom" size={18} color={c.textSecondary} />
              </TouchableOpacity>
              <TouchableOpacity style={[styles.hBtn, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.04)' }]}
                onPress={() => setIsOpen(false)} data-testid="visor-ai-close-btn">
                <MaterialCommunityIcons name="close" size={20} color={c.textSecondary} />
              </TouchableOpacity>
            </View>
          </View>

          <KeyboardAvoidingView style={styles.flex} behavior={Platform.OS === 'ios' ? 'padding' : undefined} keyboardVerticalOffset={0}>
            <ScrollView ref={scrollViewRef} style={styles.flex} contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
              {isLoadingHistory ? (
                <View style={styles.centered}>
                  <ActivityIndicator size="large" color={ACCENT} />
                  <Text style={[styles.loadTxt, { color: c.textSecondary }]}>Loading conversation...</Text>
                </View>
              ) : messages.length === 0 ? (
                <View style={styles.emptyState}>
                  {/* Welcome */}
                  <LinearGradient colors={['#10B981', '#059669']} style={styles.welcomeIcon}>
                    <MaterialCommunityIcons name="shield-star" size={44} color="#fff" />
                  </LinearGradient>
                  <Text style={[styles.welcomeTitle, { color: c.textPrimary }]} data-testid="visor-ai-welcome">
                    Namaste! I'm Visor
                  </Text>
                  <Text style={[styles.welcomeSub, { color: c.textSecondary }]}>
                    Your personal finance companion. Ask me about investments, tax planning, loans, market updates, or anything finance — in Hindi, English, Hinglish or your regional language.
                  </Text>

                  {/* Quick Prompts by Category */}
                  {QUICK_PROMPT_CATEGORIES.map((cat, ci) => (
                    <View key={ci} style={styles.promptCategory}>
                      <Text style={[styles.catTitle, { color: c.textSecondary }]}>{cat.title}</Text>
                      <View style={styles.promptRow}>
                        {cat.prompts.map((p, pi) => (
                          <TouchableOpacity
                            key={pi}
                            style={[styles.promptChip, { backgroundColor: ACCENT_BG, borderColor: isDark ? 'rgba(16,185,129,0.2)' : 'rgba(16,185,129,0.15)' }]}
                            onPress={() => sendMessage(p.prompt)}
                            data-testid={`quick-prompt-${ci}-${pi}`}
                          >
                            <MaterialCommunityIcons name={p.icon as any} size={15} color={ACCENT} />
                            <Text style={[styles.promptText, { color: c.textPrimary }]}>{p.label}</Text>
                          </TouchableOpacity>
                        ))}
                      </View>
                    </View>
                  ))}

                  {/* Disclaimer */}
                  <View style={[styles.disclaimer, { backgroundColor: isDark ? 'rgba(251,191,36,0.08)' : 'rgba(251,191,36,0.06)', borderColor: isDark ? 'rgba(251,191,36,0.15)' : 'rgba(251,191,36,0.1)' }]}>
                    <MaterialCommunityIcons name="information-outline" size={14} color="#F59E0B" />
                    <Text style={[styles.disclaimerText, { color: c.textSecondary }]}>
                      Visor educational guidance deta hai. Final financial decisions apne CA/advisor se consult karke lena.
                    </Text>
                  </View>
                </View>
              ) : (
                messages.map((msg) => (
                  <Pressable key={msg.id} onLongPress={() => deleteMessage(msg.id)} delayLongPress={600}
                    style={({ pressed }) => [{ opacity: pressed ? 0.8 : 1 }]}
                    data-testid={`chat-msg-${msg.id}`}
                  >
                    <View style={[
                      styles.bubble,
                      msg.role === 'user' ? styles.userBubble : styles.aiBubble,
                      {
                        backgroundColor: msg.role === 'user'
                          ? ACCENT
                          : isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.03)',
                      },
                    ]}>
                      {msg.role === 'assistant' && (
                        <View style={styles.aiHeader}>
                          <View style={[styles.aiDot, { backgroundColor: ACCENT }]} />
                          <Text style={[styles.aiName, { color: ACCENT }]}>Visor</Text>
                        </View>
                      )}
                      <RichText content={msg.content} color={msg.role === 'user' ? '#fff' : c.textPrimary} />

                      {/* Calculator Result Card */}
                      {msg.calculator_result && (
                        <View style={[styles.calcCard, { backgroundColor: isDark ? 'rgba(16,185,129,0.08)' : 'rgba(16,185,129,0.05)', borderColor: isDark ? 'rgba(16,185,129,0.15)' : 'rgba(16,185,129,0.1)' }]}>
                          <View style={styles.calcHeader}>
                            <MaterialCommunityIcons name="calculator-variant" size={16} color={ACCENT} />
                            <Text style={[styles.calcTitle, { color: c.textPrimary }]}>
                              {msg.calculator_result.type || 'Calculator Result'}
                            </Text>
                          </View>
                          {Object.entries(msg.calculator_result).filter(([k]) => k !== 'type').map(([key, value]) => (
                            <View key={key} style={styles.calcRow}>
                              <Text style={[styles.calcLabel, { color: c.textSecondary }]}>
                                {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                              </Text>
                              <Text style={[styles.calcValue, { color: c.textPrimary }]}>
                                {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                              </Text>
                            </View>
                          ))}
                        </View>
                      )}
                    </View>
                  </Pressable>
                ))
              )}

              {/* Thinking Indicator */}
              {isLoading && (
                <View style={[styles.bubble, styles.aiBubble, {
                  backgroundColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.03)',
                }]}>
                  <View style={styles.thinking}>
                    <Animated.View style={[styles.thinkDot, {
                      backgroundColor: ACCENT,
                      opacity: glowAnim.interpolate({ inputRange: [0, 1], outputRange: [0.3, 1] }),
                    }]} />
                    <Animated.View style={[styles.thinkDot, {
                      backgroundColor: ACCENT,
                      opacity: glowAnim.interpolate({ inputRange: [0, 0.5, 1], outputRange: [1, 0.3, 1] }),
                    }]} />
                    <Animated.View style={[styles.thinkDot, {
                      backgroundColor: ACCENT,
                      opacity: glowAnim.interpolate({ inputRange: [0, 1], outputRange: [1, 0.3] }),
                    }]} />
                    <Text style={[styles.thinkText, { color: c.textSecondary }]}>Visor soch raha hai...</Text>
                  </View>
                </View>
              )}
            </ScrollView>

            {/* Input */}
            <View style={[styles.inputWrap, {
              backgroundColor: isDark ? 'rgba(10,10,11,0.98)' : 'rgba(255,255,255,0.98)',
              borderTopColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)',
            }]}>
              <TextInput
                style={[styles.input, {
                  backgroundColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)',
                  color: c.textPrimary,
                }]}
                value={inputText}
                onChangeText={setInputText}
                placeholder="Kuch bhi pooch finance ke baare mein..."
                placeholderTextColor={c.textSecondary}
                multiline
                maxLength={1200}
                returnKeyType="send"
                onSubmitEditing={() => sendMessage(inputText)}
                data-testid="visor-ai-input"
              />
              <TouchableOpacity
                style={[styles.sendBtn, { backgroundColor: inputText.trim() ? ACCENT : isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]}
                onPress={() => sendMessage(inputText)}
                disabled={!inputText.trim() || isLoading}
                data-testid="visor-ai-send-btn"
              >
                <MaterialCommunityIcons name="send" size={18} color={inputText.trim() ? '#fff' : c.textSecondary} />
              </TouchableOpacity>
            </View>
          </KeyboardAvoidingView>
        </View>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  container: { flex: 1 },

  // FAB
  floatingBtn: { position: 'absolute', right: 20, bottom: Platform.OS === 'ios' ? 100 : 85, zIndex: 999 },
  aiButton: { width: 58, height: 58, borderRadius: 29, overflow: 'hidden', elevation: 10, shadowColor: '#10B981', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.35, shadowRadius: 10 },
  aiButtonGradient: { width: '100%', height: '100%', justifyContent: 'center', alignItems: 'center' },
  aiBadge: { position: 'absolute', top: -2, right: -2, backgroundColor: '#F59E0B', width: 20, height: 20, borderRadius: 10, justifyContent: 'center', alignItems: 'center', borderWidth: 2, borderColor: '#fff' },
  aiBadgeText: { color: '#fff', fontSize: 10, fontWeight: '800' },

  // Header
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 16, paddingTop: Platform.OS === 'ios' ? 60 : 16, paddingBottom: 12, borderBottomWidth: 1 },
  headerLeft: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  headerIcon: { width: 38, height: 38, borderRadius: 12, justifyContent: 'center', alignItems: 'center' },
  headerTitle: { fontSize: 18, fontWeight: '700' },
  headerSub: { fontSize: 11, marginTop: 1 },
  headerRight: { flexDirection: 'row', gap: 8 },
  hBtn: { width: 34, height: 34, borderRadius: 10, justifyContent: 'center', alignItems: 'center' },

  // Scroll
  scrollContent: { padding: 16, paddingBottom: 100 },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center', paddingTop: 120, gap: 12 },
  loadTxt: { fontSize: 13 },

  // Empty / Welcome
  emptyState: { alignItems: 'center', paddingTop: 30, paddingHorizontal: 16 },
  welcomeIcon: { width: 72, height: 72, borderRadius: 22, justifyContent: 'center', alignItems: 'center', marginBottom: 16 },
  welcomeTitle: { fontSize: 22, fontWeight: '700', marginBottom: 8 },
  welcomeSub: { fontSize: 13, textAlign: 'center', lineHeight: 20, marginBottom: 24, paddingHorizontal: 8 },

  // Quick Prompts
  promptCategory: { width: '100%', marginBottom: 16 },
  catTitle: { fontSize: 11, fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.8, marginBottom: 8 },
  promptRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  promptChip: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 12, paddingVertical: 8, borderRadius: 20, borderWidth: 1 },
  promptText: { fontSize: 12, fontWeight: '500' },

  // Disclaimer
  disclaimer: { flexDirection: 'row', alignItems: 'flex-start', gap: 8, marginTop: 16, padding: 12, borderRadius: 12, borderWidth: 1 },
  disclaimerText: { fontSize: 11, lineHeight: 16, flex: 1 },

  // Message Bubbles
  bubble: { maxWidth: '88%', borderRadius: 18, padding: 14, marginBottom: 10 },
  userBubble: { alignSelf: 'flex-end', borderBottomRightRadius: 4 },
  aiBubble: { alignSelf: 'flex-start', borderBottomLeftRadius: 4 },
  aiHeader: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 6 },
  aiDot: { width: 6, height: 6, borderRadius: 3 },
  aiName: { fontSize: 11, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.5 },
  messageText: { fontSize: 14, lineHeight: 21 },

  // Calculator Card
  calcCard: { marginTop: 12, padding: 12, borderRadius: 12, borderWidth: 1 },
  calcHeader: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 8 },
  calcTitle: { fontSize: 13, fontWeight: '700' },
  calcRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 3 },
  calcLabel: { fontSize: 11, flex: 1 },
  calcValue: { fontSize: 12, fontWeight: '600' },

  // Thinking
  thinking: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingVertical: 4 },
  thinkDot: { width: 7, height: 7, borderRadius: 3.5 },
  thinkText: { fontSize: 12, marginLeft: 6 },

  // Input
  inputWrap: { flexDirection: 'row', alignItems: 'flex-end', padding: 12, paddingBottom: Platform.OS === 'ios' ? 34 : 12, borderTopWidth: 1, gap: 10 },
  input: { flex: 1, minHeight: 42, maxHeight: 100, borderRadius: 21, paddingHorizontal: 16, paddingVertical: 10, fontSize: 14 },
  sendBtn: { width: 42, height: 42, borderRadius: 21, justifyContent: 'center', alignItems: 'center' },
});
