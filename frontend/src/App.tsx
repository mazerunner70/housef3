import { RouterProvider } from 'react-router-dom';
import { QueryClient } from '@tanstack/react-query';
import { useMemo } from 'react';
import { createAppRouter, setSignOutHandler } from '@/routes/router';
import './App.css';

/**
 * App Component with Data Router
 * 
 * Root application component using createBrowserRouter.
 * 
 * Features:
 * - Uses RouterProvider instead of Routes/Route
 * - Authentication is handled by components (Login) and useAuth hook
 * - Protected routes use route loaders for auth checks
 * - Supports route loaders and actions for data fetching/mutations
 * 
 * Benefits:
 * - Native useMatches() support
 * - Route-level data loading
 * - Better error handling
 * - Optimistic UI patterns
 * - Simpler auth flow without unnecessary callbacks
 */

interface AppProps {
  readonly queryClient: QueryClient;
}

function App({ queryClient }: AppProps) {
  // Create router instance
  const router = useMemo(() => {
    const newRouter = createAppRouter(queryClient);

    // Set up sign out handler
    setSignOutHandler(async () => {
      // Clear auth data
      localStorage.removeItem('authUser');
      newRouter.navigate('/login');
    });

    return newRouter;
  }, [queryClient]);

  return <RouterProvider router={router} />;
}

export default App
