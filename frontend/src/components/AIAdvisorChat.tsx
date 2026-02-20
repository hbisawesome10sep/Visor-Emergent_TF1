import React, { useState, useRef, useEffect } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, Modal, TextInput,
  ScrollView, KeyboardAvoidingView, Platform, ActivityIndicator,
  Dimensions, Animated, Alert, Pressable,
} from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { BlurView } from 'expo-blur';
import { LinearGradient } from 'expo-linear-gradient';
import { apiRequest } from '../utils/api';
import { useScreenContext } from '../context/ScreenContext';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

type Message = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  calculator_result?: any;
  created_at: string;
};

type Props = {
  token: string | null;
  colors: any;
  isDark: boolean;
};

const QUICK_PROMPTS = [
  { icon: 'calculator', label: 'SIP Calculator', prompt: 'Help me calculate SIP returns for ₹10,000 monthly investment' },
  { icon: 'home', label: 'Home Loan EMI', prompt: 'Calculate EMI for a ₹50 lakh home loan at 8.5% for 20 years' },
  { icon: 'file-document', label: 'Tax Planning', prompt: 'How can I save tax under Section 80C? What are my options?' },
  { icon: 'chart-line', label: 'Investment Advice', prompt: 'Based on my finances, what should I invest in?' },
  { icon: 'shield-check', label: 'Emergency Fund', prompt: 'How much emergency fund should I have? Am I on track?' },
  { icon: 'trending-up', label: 'Retirement Planning', prompt: 'Help me plan for retirement. Calculate my FIRE number.' },
];

export default function AIAdvisorChat({ token, colors, isDark }: Props) {
  const { getScreenContext, setCurrentScreen } = useScreenContext();
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const scrollViewRef = useRef<ScrollView>(null);
  const pulseAnim = useRef(new Animated.Value(1)).current;

  // Pulse animation for the floating button
  useEffect(() => {
    const pulse = Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, { toValue: 1.1, duration: 1000, useNativeDriver: true }),
        Animated.timing(pulseAnim, { toValue: 1, duration: 1000, useNativeDriver: true }),
      ])
    );
    pulse.start();
    return () => pulse.stop();
  }, []);

  // Load chat history on mount
  useEffect(() => {
    if (token && isOpen) {
      loadHistory();
    }
  }, [token, isOpen]);

  const loadHistory = async () => {
    if (!token) return;
    setIsLoadingHistory(true);
    try {
      const history = await apiRequest('/ai/history', { token });
      setMessages(history.map((h: any) => ({
        id: h.id,
        role: h.role,
        content: h.content,
        created_at: h.created_at,
      })));
    } catch (e) {
      console.error('Failed to load history:', e);
    } finally {
      setIsLoadingHistory(false);
    }
  };

  const sendMessage = async (text: string) => {
    if (!text.trim() || !token || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: text.trim(),
      created_at: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputText('');
    setIsLoading(true);

    // Scroll to bottom
    setTimeout(() => scrollViewRef.current?.scrollToEnd({ animated: true }), 100);

    try {
      // Get current screen context for AI awareness
      const screenContext = getScreenContext();
      
      const response = await apiRequest('/ai/chat', {
        method: 'POST',
        token,
        body: { 
          message: text.trim(),
          screen_context: screenContext,
        },
      });

      // Update user message ID with server-assigned UUID (for delete to work)
      if (response.user_msg_id) {
        setMessages(prev => prev.map(m => 
          m.id === userMessage.id ? { ...m, id: response.user_msg_id } : m
        ));
      }

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.content,
        calculator_result: response.calculator_result,
        created_at: new Date().toISOString(),
      };

      setMessages(prev => [...prev, assistantMessage]);
      setTimeout(() => scrollViewRef.current?.scrollToEnd({ animated: true }), 100);
    } catch (e: any) {
      console.error('Chat error:', e);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `Sorry, I encountered an error. Please try again. (${e.message || 'Unknown error'})`,
        created_at: new Date().toISOString(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const clearChat = async () => {
    if (!token) return;
    try {
      await apiRequest('/ai/history', { method: 'DELETE', token });
      setMessages([]);
    } catch (e) {
      console.error('Failed to clear history:', e);
    }
  };

  const deleteMessage = async (messageId: string) => {
    Alert.alert(
      'Delete Message',
      'Are you sure you want to delete this message?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              await apiRequest(`/ai/message/${messageId}`, { method: 'DELETE', token });
              setMessages(prev => prev.filter(m => m.id !== messageId));
            } catch (e) {
              console.error('Failed to delete message:', e);
            }
          },
        },
      ]
    );
  };

  const formatMessage = (content: string) => {
    // Simple markdown-like formatting
    return content
      .replace(/\*\*(.*?)\*\*/g, '$1') // Remove bold markers for now
      .replace(/\*(.*?)\*/g, '$1'); // Remove italic markers
  };

  return (
    <>
      {/* Floating AI Button */}
      <Animated.View style={[styles.floatingBtn, { transform: [{ scale: pulseAnim }] }]}>
        <TouchableOpacity
          style={styles.aiButton}
          onPress={() => setIsOpen(true)}
          activeOpacity={0.9}
        >
          <LinearGradient
            colors={['#8B5CF6', '#6366F1', '#4F46E5']}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 1 }}
            style={styles.aiButtonGradient}
          >
            <MaterialCommunityIcons name="robot" size={26} color="#fff" />
          </LinearGradient>
        </TouchableOpacity>
        <View style={styles.aiBadge}>
          <Text style={styles.aiBadgeText}>AI</Text>
        </View>
      </Animated.View>

      {/* Chat Modal */}
      <Modal
        visible={isOpen}
        animationType="slide"
        transparent={false}
        onRequestClose={() => setIsOpen(false)}
      >
        <View style={[styles.container, { backgroundColor: colors.background }]}>
          {/* Header */}
          <View style={[styles.header, {
            backgroundColor: isDark ? 'rgba(10,10,11,0.98)' : 'rgba(255,255,255,0.98)',
            borderBottomColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)',
          }]}>
            <View style={styles.headerLeft}>
              <LinearGradient
                colors={['#8B5CF6', '#6366F1']}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 0 }}
                style={styles.headerIcon}
              >
                <MaterialCommunityIcons name="robot" size={22} color="#fff" />
              </LinearGradient>
              <View style={styles.headerText}>
                <Text style={[styles.headerTitle, { color: colors.textPrimary }]}>Visor</Text>
                <Text style={[styles.headerSubtitle, { color: colors.textSecondary }]}>
                  Your Financial Advisor
                </Text>
              </View>
            </View>
            <View style={styles.headerRight}>
              <TouchableOpacity
                style={[styles.headerBtn, { backgroundColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.05)' }]}
                onPress={clearChat}
              >
                <MaterialCommunityIcons name="delete-outline" size={20} color={colors.textSecondary} />
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.headerBtn, { backgroundColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.05)' }]}
                onPress={() => setIsOpen(false)}
              >
                <MaterialCommunityIcons name="close" size={22} color={colors.textSecondary} />
              </TouchableOpacity>
            </View>
          </View>

          {/* Messages */}
          <KeyboardAvoidingView
            style={styles.messagesContainer}
            behavior={Platform.OS === 'ios' ? 'padding' : undefined}
            keyboardVerticalOffset={90}
          >
            <ScrollView
              ref={scrollViewRef}
              style={styles.messagesList}
              contentContainerStyle={styles.messagesContent}
              showsVerticalScrollIndicator={false}
            >
              {isLoadingHistory ? (
                <View style={styles.loadingContainer}>
                  <ActivityIndicator size="large" color="#8B5CF6" />
                  <Text style={[styles.loadingText, { color: colors.textSecondary }]}>
                    Loading conversation...
                  </Text>
                </View>
              ) : messages.length === 0 ? (
                <View style={styles.emptyState}>
                  <LinearGradient
                    colors={['#8B5CF6', '#6366F1']}
                    style={styles.emptyIcon}
                  >
                    <MaterialCommunityIcons name="robot-happy" size={48} color="#fff" />
                  </LinearGradient>
                  <Text style={[styles.emptyTitle, { color: colors.textPrimary }]}>
                    Hi! I'm Visor 👋
                  </Text>
                  <Text style={[styles.emptySubtitle, { color: colors.textSecondary }]}>
                    Your personal Indian financial advisor. I understand your finances deeply
                    and can help with tax planning, investments, loans, and more!
                  </Text>

                  {/* Quick prompts */}
                  <Text style={[styles.quickTitle, { color: colors.textPrimary }]}>
                    Try asking me:
                  </Text>
                  <View style={styles.quickPrompts}>
                    {QUICK_PROMPTS.map((prompt, index) => (
                      <TouchableOpacity
                        key={index}
                        style={[styles.quickChip, {
                          backgroundColor: isDark ? 'rgba(139,92,246,0.15)' : 'rgba(139,92,246,0.1)',
                          borderColor: isDark ? 'rgba(139,92,246,0.3)' : 'rgba(139,92,246,0.2)',
                        }]}
                        onPress={() => sendMessage(prompt.prompt)}
                      >
                        <MaterialCommunityIcons name={prompt.icon as any} size={16} color="#8B5CF6" />
                        <Text style={[styles.quickChipText, { color: colors.textPrimary }]}>
                          {prompt.label}
                        </Text>
                      </TouchableOpacity>
                    ))}
                  </View>
                </View>
              ) : (
                messages.map((msg) => (
                  <Pressable
                    key={msg.id}
                    onLongPress={() => deleteMessage(msg.id)}
                    delayLongPress={500}
                    style={({ pressed }) => [{ opacity: pressed ? 0.7 : 1 }]}
                    testID={`chat-message-${msg.id}`}
                  >
                    <View
                      style={[
                        styles.messageBubble,
                        msg.role === 'user' ? styles.userBubble : styles.assistantBubble,
                        {
                          backgroundColor: msg.role === 'user'
                            ? '#8B5CF6'
                            : isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.04)',
                        },
                      ]}
                    >
                    {msg.role === 'assistant' && (
                      <View style={styles.assistantHeader}>
                        <MaterialCommunityIcons name="robot" size={16} color="#8B5CF6" />
                        <Text style={[styles.assistantName, { color: '#8B5CF6' }]}>Visor</Text>
                      </View>
                    )}
                    <Text
                      style={[
                        styles.messageText,
                        { color: msg.role === 'user' ? '#fff' : colors.textPrimary },
                      ]}
                    >
                      {formatMessage(msg.content)}
                    </Text>
                    
                    {/* Calculator Result */}
                    {msg.calculator_result && (
                      <View style={[styles.calculatorResult, {
                        backgroundColor: isDark ? 'rgba(139,92,246,0.1)' : 'rgba(139,92,246,0.08)',
                      }]}>
                        <Text style={[styles.calcTitle, { color: colors.textPrimary }]}>
                          📊 Calculator Result
                        </Text>
                        {Object.entries(msg.calculator_result).map(([key, value]) => (
                          <View key={key} style={styles.calcRow}>
                            <Text style={[styles.calcLabel, { color: colors.textSecondary }]}>
                              {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                            </Text>
                            <Text style={[styles.calcValue, { color: colors.textPrimary }]}>
                              {typeof value === 'number' ? `₹${value.toLocaleString('en-IN')}` : String(value)}
                            </Text>
                          </View>
                        ))}
                      </View>
                    )}
                  </View>
                  </Pressable>
                ))
              )}

              {isLoading && (
                <View style={[styles.messageBubble, styles.assistantBubble, {
                  backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.04)',
                }]}>
                  <View style={styles.typingIndicator}>
                    <ActivityIndicator size="small" color="#8B5CF6" />
                    <Text style={[styles.typingText, { color: colors.textSecondary }]}>
                      Visor is thinking...
                    </Text>
                  </View>
                </View>
              )}
            </ScrollView>

            {/* Input Area */}
            <View style={[styles.inputContainer, {
              backgroundColor: isDark ? 'rgba(10,10,11,0.98)' : 'rgba(255,255,255,0.98)',
              borderTopColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)',
            }]}>
              <TextInput
                style={[styles.input, {
                  backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.04)',
                  color: colors.textPrimary,
                }]}
                value={inputText}
                onChangeText={setInputText}
                placeholder="Ask about investments, taxes, loans..."
                placeholderTextColor={colors.textSecondary}
                multiline
                maxLength={1000}
                returnKeyType="send"
                onSubmitEditing={() => sendMessage(inputText)}
              />
              <TouchableOpacity
                style={[styles.sendBtn, {
                  backgroundColor: inputText.trim() ? '#8B5CF6' : isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)',
                }]}
                onPress={() => sendMessage(inputText)}
                disabled={!inputText.trim() || isLoading}
              >
                <MaterialCommunityIcons
                  name="send"
                  size={20}
                  color={inputText.trim() ? '#fff' : colors.textSecondary}
                />
              </TouchableOpacity>
            </View>
          </KeyboardAvoidingView>
        </View>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  // Floating button
  floatingBtn: {
    position: 'absolute',
    right: 20,
    bottom: Platform.OS === 'ios' ? 100 : 85,
    zIndex: 999,
  },
  aiButton: {
    width: 56,
    height: 56,
    borderRadius: 28,
    overflow: 'hidden',
    elevation: 8,
    shadowColor: '#8B5CF6',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.4,
    shadowRadius: 8,
  },
  aiButtonGradient: {
    width: '100%',
    height: '100%',
    justifyContent: 'center',
    alignItems: 'center',
  },
  aiBadge: {
    position: 'absolute',
    top: -4,
    right: -4,
    backgroundColor: '#10B981',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 8,
    borderWidth: 2,
    borderColor: '#fff',
  },
  aiBadgeText: {
    color: '#fff',
    fontSize: 10,
    fontFamily: 'DM Sans', fontWeight: '700' as any,
  },

  // Container
  container: {
    flex: 1,
  },

  // Header
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingTop: Platform.OS === 'ios' ? 60 : 16,
    paddingBottom: 12,
    borderBottomWidth: 1,
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  headerIcon: {
    width: 40,
    height: 40,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
  },
  headerText: {
    gap: 2,
  },
  headerTitle: {
    fontSize: 18,
    fontFamily: 'DM Sans', fontWeight: '700' as any,
  },
  headerSubtitle: {
    fontSize: 12,
  },
  headerRight: {
    flexDirection: 'row',
    gap: 8,
  },
  headerBtn: {
    width: 36,
    height: 36,
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
  },

  // Messages
  messagesContainer: {
    flex: 1,
  },
  messagesList: {
    flex: 1,
  },
  messagesContent: {
    padding: 16,
    paddingBottom: 100,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingTop: 100,
    gap: 12,
  },
  loadingText: {
    fontSize: 14,
  },

  // Empty state
  emptyState: {
    alignItems: 'center',
    paddingTop: 40,
    paddingHorizontal: 20,
  },
  emptyIcon: {
    width: 80,
    height: 80,
    borderRadius: 24,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 20,
  },
  emptyTitle: {
    fontSize: 22,
    fontFamily: 'DM Sans', fontWeight: '700' as any,
    marginBottom: 8,
  },
  emptySubtitle: {
    fontSize: 14,
    textAlign: 'center',
    lineHeight: 22,
    marginBottom: 24,
  },
  quickTitle: {
    fontSize: 15,
    fontFamily: 'DM Sans', fontWeight: '600' as any,
    marginBottom: 12,
  },
  quickPrompts: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: 8,
  },
  quickChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 16,
    borderWidth: 1,
  },
  quickChipText: {
    fontSize: 13,
    fontFamily: 'DM Sans', fontWeight: '500' as any,
  },

  // Message bubbles
  messageBubble: {
    maxWidth: '85%',
    borderRadius: 16,
    padding: 12,
    marginBottom: 12,
  },
  userBubble: {
    alignSelf: 'flex-end',
    borderBottomRightRadius: 4,
  },
  assistantBubble: {
    alignSelf: 'flex-start',
    borderBottomLeftRadius: 4,
  },
  assistantHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginBottom: 6,
  },
  assistantName: {
    fontSize: 12,
    fontFamily: 'DM Sans', fontWeight: '600' as any,
  },
  messageText: {
    fontSize: 15,
    lineHeight: 22,
  },

  // Calculator result
  calculatorResult: {
    marginTop: 12,
    padding: 12,
    borderRadius: 12,
  },
  calcTitle: {
    fontSize: 14,
    fontFamily: 'DM Sans', fontWeight: '700' as any,
    marginBottom: 8,
  },
  calcRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 4,
  },
  calcLabel: {
    fontSize: 12,
    flex: 1,
  },
  calcValue: {
    fontSize: 13,
    fontFamily: 'DM Sans', fontWeight: '600' as any,
  },

  // Typing indicator
  typingIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  typingText: {
    fontSize: 13,
  },

  // Input
  inputContainer: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    flexDirection: 'row',
    alignItems: 'flex-end',
    padding: 12,
    paddingBottom: Platform.OS === 'ios' ? 34 : 12,
    borderTopWidth: 1,
    gap: 10,
  },
  input: {
    flex: 1,
    minHeight: 44,
    maxHeight: 100,
    borderRadius: 22,
    paddingHorizontal: 16,
    paddingVertical: 10,
    fontSize: 15,
  },
  sendBtn: {
    width: 44,
    height: 44,
    borderRadius: 22,
    justifyContent: 'center',
    alignItems: 'center',
  },
});
