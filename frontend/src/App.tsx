import { RouterProvider } from 'react-router-dom';
import { QueryClient } from '@tanstack/react-query';
import { useState, useMemo } from 'react';
import { createAppRouter, setAuthHandlers } from '@/routes/router';
import './App.css';

/**
 * App Component with Data Router
 * 
 * Root application component using createBrowserRouter.
 * 
 * Features:
 * - Uses RouterProvider instead of Routes/Route
 * - Authentication is handled via route loaders
 * - Auth state is managed by the router
 * - Supports route loaders and actions for data fetching/mutations
 * 
 * Benefits:
 * - Native useMatches() support
 * - Route-level data loading
 * - Better error handling
 * - Optimistic UI patterns
 * - Data persistence callbacks on route changes
 */

interface AppProps {
  readonly queryClient: QueryClient;
}

function App({ queryClient }: AppProps) {
  const [authKey, setAuthKey] = useState(0);

  // Create router instance with auth handlers
  const router = useMemo(() => {
    const newRouter = createAppRouter(queryClient);

    // Set up auth handlers that trigger router refresh
    setAuthHandlers({
      handleLogin: () => {
        setAuthKey(prev => prev + 1);
        newRouter.navigate('/');
      },
      handleSignOut: () => {
        // Clear auth data
        localStorage.removeItem('currentUser');
        setAuthKey(prev => prev + 1);
        newRouter.navigate('/login');
      }
    });

    return newRouter;
  }, [queryClient, authKey]);

  return <RouterProvider router={router} />;
}

export default App
