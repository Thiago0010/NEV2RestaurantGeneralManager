// Auth Context - replaces Base44 auth
import React, { createContext, useState, useContext, useEffect, useCallback } from 'react';
import { api as restaurantApi } from '@/lib/restaurant-context';
import { authApi } from '@/api/client';
import { useToast } from '@/components/ui/use-toast';
import { extractErrorMessage } from '@/lib/error';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoadingAuth, setIsLoadingAuth] = useState(true);
  const [isLoadingPublicSettings, setIsLoadingPublicSettings] = useState(true);
  const [authError, setAuthError] = useState(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [appPublicSettings, setAppPublicSettings] = useState(null);
  const { toast } = useToast();

  const checkUserAuth = useCallback(async () => {
    try {
      setIsLoadingAuth(true);
      const currentUser = await authApi.getMe();
      setUser(currentUser);
      setIsAuthenticated(true);
      setIsLoadingAuth(false);
      setAuthChecked(true);
    } catch (error) {
      console.error('User auth check failed:', error);
      setIsLoadingAuth(false);
      setIsAuthenticated(false);
      setAuthChecked(true);

      if (error.status === 401 || error.status === 403) {
        setAuthError({
          type: 'auth_required',
          message: 'Authentication required'
        });
        // Clear invalid token
        localStorage.removeItem('access_token');
      }
    }
  }, []);

  const checkAppState = useCallback(async () => {
    try {
      setIsLoadingPublicSettings(true);
      setAuthError(null);

      // Check if we have a token
      const token = localStorage.getItem('access_token');
      if (token) {
        await checkUserAuth();
      } else {
        setIsLoadingAuth(false);
        setIsAuthenticated(false);
        setAuthChecked(true);
      }
      setIsLoadingPublicSettings(false);
    } catch (error) {
      console.error('Unexpected error:', error);
      setAuthError({
        type: 'unknown',
        message: error.message || 'An unexpected error occurred'
      });
      setIsLoadingPublicSettings(false);
      setIsLoadingAuth(false);
    }
  }, [checkUserAuth]);

  useEffect(() => {
    checkAppState();
  }, [checkAppState]);

  const login = async (email, password) => {
    try {
      const response = await restaurantApi.auth.login(email, password);
      setUser(response.user);
      setIsAuthenticated(true);
      setAuthError(null);
      toast({ title: 'Login realizado com sucesso!' });
      return response;
    } catch (error) {
      const message = extractErrorMessage(error, 'E-mail ou senha inválidos');
      toast({ title: 'Erro no login', description: message, variant: 'destructive' });
      throw new Error(message);
    }
  };

  const register = async (email, password, fullName, restaurantName, restaurantSlug, secretKey = "123") => {
    try {
      const response = await restaurantApi.auth.register(email, password, fullName, restaurantName, restaurantSlug, secretKey);
      setUser(response.user);
      setIsAuthenticated(true);
      setAuthError(null);
      toast({ title: 'Conta criada com sucesso!' });
      return response;
    } catch (error) {
      const message = extractErrorMessage(error, 'Erro ao criar conta.');
      toast({ title: 'Erro no cadastro', description: message, variant: 'destructive' });
      throw new Error(message);
    }
  };

  const logout = (shouldRedirect = true) => {
    setUser(null);
    setIsAuthenticated(false);
    localStorage.removeItem('access_token');

    if (shouldRedirect) {
      // Use replace so the user can't navigate back into a protected page
      window.location.replace('/login');
    }
  };

  const navigateToLogin = () => {
    window.location.replace('/login');
  };

  return (
    <AuthContext.Provider value={{
      user,
      isAuthenticated,
      isLoadingAuth,
      isLoadingPublicSettings,
      authError,
      appPublicSettings,
      authChecked,
      logout,
      navigateToLogin,
      checkUserAuth,
      checkAppState,
      login,
      register,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};