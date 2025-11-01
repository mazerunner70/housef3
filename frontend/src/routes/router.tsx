import { createBrowserRouter, redirect, LoaderFunctionArgs, Link } from 'react-router-dom';
import { QueryClient } from '@tanstack/react-query';
import Login from '@/components/business/auth/Login';
import NewUILayout from '@/layouts/NewUILayout';
import { isAuthenticated, getCurrentUser, refreshToken } from '@/services/AuthService';
import { appRoutes } from './appRoutes';

/**
 * Router Configuration with Data Router
 * 
 * This file creates the application router using createBrowserRouter,
 * which provides:
 * - Route loaders for data fetching
 * - Route actions for mutations
 * - Native useMatches() support
 * - Better error handling
 * - Optimistic UI patterns
 * 
 * Auth Flow:
 * - Root loader checks authentication
 * - Redirects to /login if not authenticated
 * - Automatically refreshes tokens if needed
 * - Protected routes inherit auth check from parent
 */

// Store handlers for auth state changes (set by App component)
let authHandlers: {
    handleLogin: () => void;
    handleSignOut: () => void;
} | null = null;

export const setAuthHandlers = (handlers: typeof authHandlers) => {
    authHandlers = handlers;
};

/**
 * Root loader - checks authentication for all routes
 * This runs before any route is rendered
 */
export const rootLoader = async () => {
    try {
        const currentUser = getCurrentUser();

        if (!currentUser) {
            return { authenticated: false };
        }

        // Check if token is still valid
        if (isAuthenticated()) {
            return { authenticated: true, user: currentUser };
        }

        // Try to refresh token if expired
        if (currentUser.refreshToken) {
            try {
                await refreshToken(currentUser.refreshToken);
                return { authenticated: true, user: currentUser };
            } catch (error) {
                console.error('Failed to refresh token:', error);
                return { authenticated: false };
            }
        }

        return { authenticated: false };
    } catch (error) {
        console.error('Authentication check error:', error);
        return { authenticated: false };
    }
};

/**
 * Auth guard loader - redirects to login if not authenticated
 * Used for protected routes
 */
export const protectedLoader = async () => {
    const authStatus = await rootLoader();

    if (!authStatus.authenticated) {
        return redirect('/login');
    }

    return authStatus;
};

/**
 * Login loader - redirects to home if already authenticated
 */
export const loginLoader = async () => {
    const authStatus = await rootLoader();

    if (authStatus.authenticated) {
        return redirect('/');
    }

    return null;
};

/**
 * Example route loader with data fetching
 * This can be used as a template for other loaders
 */
export const exampleDataLoader = async ({ params }: LoaderFunctionArgs) => {
    // Check auth first
    const authStatus = await rootLoader();
    if (!authStatus.authenticated) {
        return redirect('/login');
    }

    // Fetch data here
    // You can integrate with React Query or fetch directly
    // Example:
    // const data = await fetch(`/api/resource/${params.id}`).then(r => r.json());

    return {
        // Return data that will be available via useLoaderData()
        params,
        timestamp: new Date().toISOString()
    };
};

/**
 * Create the router with data router features
 */
export const createAppRouter = (queryClient: QueryClient) => {
    return createBrowserRouter([
        // Login route
        {
            path: '/login',
            element: <Login onLoginSuccess={() => authHandlers?.handleLogin()} />,
            loader: loginLoader,
            errorElement: <div>Error loading login page</div>
        },

        // Protected routes wrapped in layout
        {
            path: '/',
            element: <NewUILayout onSignOut={() => authHandlers?.handleSignOut()} />,
            loader: protectedLoader,
            errorElement: <div>Something went wrong. Please refresh the page.</div>,
            // Add Home breadcrumb to root so all child routes have at least 2 breadcrumbs
            handle: {
                breadcrumb: () => <Link to="/">Home</Link>
            },
            children: appRoutes.map(route => ({
                ...route,
                // Explicitly preserve handle
                handle: route.handle,
                // You can add loaders to individual routes here
                // Example:
                // loader: route.path === 'accounts/:accountId' 
                //   ? accountLoader 
                //   : route.loader,
            }))
        },

        // Catch-all 404
        {
            path: '*',
            element: <div>
                <h1>404 - Page Not Found</h1>
                <p>The page you're looking for doesn't exist.</p>
                <a href="/">Go Home</a>
            </div>
        }
    ]);
};

/**
 * Example of how to use loaders in your components:
 * 
 * ```tsx
 * import { useLoaderData } from 'react-router-dom';
 * 
 * export const AccountDetailPage = () => {
 *   const { account } = useLoaderData() as { account: Account };
 *   return <div>{account.name}</div>;
 * };
 * ```
 * 
 * Example of how to add a loader to a route:
 * 
 * ```tsx
 * {
 *   path: 'accounts/:accountId',
 *   element: <AccountDetailPage />,
 *   loader: async ({ params }) => {
 *     const account = await fetchAccount(params.accountId);
 *     return { account };
 *   }
 * }
 * ```
 * 
 * Example of how to use actions for mutations:
 * 
 * ```tsx
 * import { Form, useActionData } from 'react-router-dom';
 * 
 * // In your component:
 * <Form method="post">
 *   <input name="name" />
 *   <button type="submit">Save</button>
 * </Form>
 * 
 * // In your route config:
 * {
 *   path: 'accounts/:accountId',
 *   element: <AccountDetailPage />,
 *   action: async ({ request, params }) => {
 *     const formData = await request.formData();
 *     const name = formData.get('name');
 *     await updateAccount(params.accountId, { name });
 *     return { success: true };
 *   }
 * }
 * ```
 */

