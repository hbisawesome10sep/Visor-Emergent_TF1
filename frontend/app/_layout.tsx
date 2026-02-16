import { useEffect, useCallback, useState } from 'react';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { View, ActivityIndicator, Platform } from 'react-native';
import {
  useFonts,
  SpaceGrotesk_400Regular,
  SpaceGrotesk_500Medium,
  SpaceGrotesk_600SemiBold,
  SpaceGrotesk_700Bold,
} from '@expo-google-fonts/space-grotesk';
import {
  Outfit_400Regular,
  Outfit_500Medium,
  Outfit_600SemiBold,
  Outfit_700Bold,
  Outfit_800ExtraBold,
} from '@expo-google-fonts/outfit';
import * as SplashScreen from 'expo-splash-screen';
import { AuthProvider } from '../src/context/AuthContext';
import { ThemeProvider, useTheme } from '../src/context/ThemeContext';

SplashScreen.preventAutoHideAsync();

function InnerLayout() {
  const { isDark, colors } = useTheme();
  return (
    <>
      <StatusBar style={isDark ? 'light' : 'dark'} />
      <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: colors.background } }}>
        <Stack.Screen name="index" />
        <Stack.Screen name="(auth)" />
        <Stack.Screen name="(tabs)" />
      </Stack>
    </>
  );
}

export default function RootLayout() {
  const [fontsLoaded, fontError] = useFonts({
    SpaceGrotesk_400Regular,
    SpaceGrotesk_500Medium,
    SpaceGrotesk_600SemiBold,
    SpaceGrotesk_700Bold,
    Outfit_400Regular,
    Outfit_500Medium,
    Outfit_600SemiBold,
    Outfit_700Bold,
    Outfit_800ExtraBold,
  });

  // On web, inject Google Fonts via CSS and register font-face aliases
  useEffect(() => {
    if (Platform.OS === 'web') {
      const style = document.createElement('style');
      style.textContent = `
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap');
        
        @font-face { font-family: 'SpaceGrotesk_400Regular'; src: local('Space Grotesk'), local('SpaceGrotesk-Regular'); font-weight: 400; }
        @font-face { font-family: 'SpaceGrotesk_500Medium'; src: local('Space Grotesk'), local('SpaceGrotesk-Medium'); font-weight: 500; }
        @font-face { font-family: 'SpaceGrotesk_600SemiBold'; src: local('Space Grotesk'), local('SpaceGrotesk-SemiBold'); font-weight: 600; }
        @font-face { font-family: 'SpaceGrotesk_700Bold'; src: local('Space Grotesk'), local('SpaceGrotesk-Bold'); font-weight: 700; }
        @font-face { font-family: 'Outfit_400Regular'; src: local('Outfit'), local('Outfit-Regular'); font-weight: 400; }
        @font-face { font-family: 'Outfit_500Medium'; src: local('Outfit'), local('Outfit-Medium'); font-weight: 500; }
        @font-face { font-family: 'Outfit_600SemiBold'; src: local('Outfit'), local('Outfit-SemiBold'); font-weight: 600; }
        @font-face { font-family: 'Outfit_700Bold'; src: local('Outfit'), local('Outfit-Bold'); font-weight: 700; }
        @font-face { font-family: 'Outfit_800ExtraBold'; src: local('Outfit'), local('Outfit-ExtraBold'); font-weight: 800; }
      `;
      document.head.appendChild(style);
    }
  }, []);

  const isReady = fontsLoaded || fontError || Platform.OS === 'web';

  const onLayoutReady = useCallback(async () => {
    if (isReady) {
      await SplashScreen.hideAsync();
    }
  }, [isReady]);

  useEffect(() => {
    onLayoutReady();
  }, [onLayoutReady]);

  if (!isReady) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#000' }}>
        <ActivityIndicator size="large" color="#00FFD1" />
      </View>
    );
  }

  return (
    <ThemeProvider>
      <AuthProvider>
        <InnerLayout />
      </AuthProvider>
    </ThemeProvider>
  );
}
