import { Toaster } from "@/components/ui/toaster"
import { QueryClientProvider } from '@tanstack/react-query'
import { queryClientInstance } from '@/lib/query-client'
import { BrowserRouter as Router, Route, Routes, Outlet, useLocation, Navigate } from 'react-router-dom'
import { useEffect } from 'react'
import PageNotFound from './lib/PageNotFound'
import { AuthProvider, useAuth } from '@/lib/AuthContext'
import UserNotRegisteredError from '@/components/UserNotRegisteredError'
import ErrorBoundary from '@/components/ErrorBoundary'
import ScrollToTop from './components/ScrollToTop'
// Auth pages
import Login from '@/pages/Login'
import Register from '@/pages/Register'
import ForgotPassword from '@/pages/ForgotPassword'
import ResetPassword from '@/pages/ResetPassword'
// App
import AppLayout from '@/components/AppLayout'
import { RestaurantProvider } from '@/lib/restaurant-context'
import Onboarding from '@/pages/Onboarding'
import Home from '@/pages/Home'
import Tables from '@/pages/Tables'
import Menu from '@/pages/Menu'
import Kitchen from '@/pages/Kitchen'
import Waiter from '@/pages/Waiter'
import QRCodes from '@/pages/QRCodes'
import Reports from '@/pages/Reports'
import Employees from '@/pages/Employees'
import Settings from '@/pages/Settings'
import CustomerMenu from '@/pages/CustomerMenu'

const GuardedApp = () => {
  const { isLoadingAuth, isLoadingPublicSettings, authError, isAuthenticated, navigateToLogin } = useAuth();
  const location = useLocation();
  const isOnboardingRoute = location.pathname === '/onboarding';

  // Effect-driven redirect (no side effects during render)
  useEffect(() => {
    if (
      !isLoadingPublicSettings &&
      !isLoadingAuth &&
      authError?.type === 'auth_required' &&
      !isOnboardingRoute
    ) {
      navigateToLogin();
    }
  }, [isLoadingPublicSettings, isLoadingAuth, authError, isOnboardingRoute, navigateToLogin]);

  if (isLoadingPublicSettings || isLoadingAuth) {
    return (
      <div className="fixed inset-0 flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-border border-t-primary rounded-full animate-spin"></div>
      </div>
    );
  }

  if (authError?.type === 'user_not_registered') {
    return <UserNotRegisteredError />;
  }

  if (!isAuthenticated) {
    // While the effect redirects, render nothing to avoid protected content flash
    return null;
  }

  return <RestaurantProvider><Outlet /></RestaurantProvider>;
};

function App() {
  return (
    <AuthProvider>
      <QueryClientProvider client={queryClientInstance}>
        <Router>
          <ScrollToTop />
          <Routes>
            {/* Public auth */}
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<ErrorBoundary><Register /></ErrorBoundary>} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password" element={<ResetPassword />} />

            {/* Public customer menu via QR */}
            <Route path="/r/:slug/table/:num" element={<CustomerMenu />} />

            {/* Authenticated app */}
            <Route element={<GuardedApp />}>
              <Route path="/onboarding" element={<Onboarding />} />
              <Route element={<AppLayout />}>
                <Route path="/" element={<Home />} />
                <Route path="/tables" element={<Tables />} />
                <Route path="/menu" element={<Menu />} />
                <Route path="/kitchen" element={<Kitchen />} />
                <Route path="/waiter" element={<Waiter />} />
                <Route path="/qr-codes" element={<QRCodes />} />
                <Route path="/reports" element={<Reports />} />
                <Route path="/employees" element={<Employees />} />
                <Route path="/settings" element={<Settings />} />
              </Route>
            </Route>

            <Route path="*" element={<PageNotFound />} />
          </Routes>
          <Toaster />
        </Router>
      </QueryClientProvider>
    </AuthProvider>
  )
}

export default App