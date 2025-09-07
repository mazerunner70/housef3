import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// Maximum URL length before compression
const MAX_URL_LENGTH = 1500;

// Maximum number of session URLs to keep
const MAX_SESSION_URLS = 30;

// Session URL entry interface
export interface SessionUrlEntry {
    id: string;
    url: string;
    navigationState: NavigationSessionState;
    accessCount: number;
    lastAccessed: number;
    created: number;
}

// Navigation state that gets stored in sessions
export interface NavigationSessionState {
    currentView: string;
    selectedAccountId?: string;
    selectedFileId?: string;
    selectedTransactionId?: string;
    context?: {
        filter?: string;
        sort?: string;
        page?: string;
        dateRange?: string;
        categoryId?: string;
        tagId?: string;
        searchQuery?: string;
        viewMode?: string;
        groupBy?: string;
    };
    breadcrumb?: Array<{
        label: string;
        level: number;
        accountId?: string;
        fileId?: string;
        transactionId?: string;
    }>;
}

// Session URL store interface
export interface SessionUrlStore {
    // Session entries (LRU cache)
    sessions: Map<string, SessionUrlEntry>;

    // Actions
    generateSessionUrl: (navigationState: NavigationSessionState) => string;
    resolveSessionUrl: (url: string) => NavigationSessionState | null;
    getSessionEntry: (sessionId: string) => SessionUrlEntry | null;
    cleanupOldSessions: () => void;
    clearAllSessions: () => void;

    // Utilities
    isSessionUrl: (url: string) => boolean;
    getSessionStats: () => {
        totalSessions: number;
        oldestSession: number;
        newestSession: number;
        mostUsedSession: SessionUrlEntry | null;
    };
}

// Generate a short, unique session ID
const generateSessionId = (): string => {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    let result = '';
    for (let i = 0; i < 8; i++) {
        result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return result;
};

// Generate a hash for navigation state to detect duplicates
const generateStateHash = (state: NavigationSessionState): string => {
    const stateString = JSON.stringify({
        currentView: state.currentView,
        selectedAccountId: state.selectedAccountId,
        selectedFileId: state.selectedFileId,
        selectedTransactionId: state.selectedTransactionId,
        context: state.context
    });

    // Simple hash function
    let hash = 0;
    for (let i = 0; i < stateString.length; i++) {
        const char = stateString.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash; // Convert to 32-bit integer
    }
    return Math.abs(hash).toString(36);
};

// Generate traditional URL from navigation state
const generateTraditionalUrl = (state: NavigationSessionState): string => {
    let url = '/accounts';

    if (state.selectedAccountId) {
        url += `/${state.selectedAccountId}`;

        if (state.selectedFileId && state.selectedTransactionId) {
            url += `/files/${state.selectedFileId}/transactions/${state.selectedTransactionId}`;
        } else if (state.selectedFileId) {
            url += `/files/${state.selectedFileId}`;
        } else if (state.selectedTransactionId) {
            url += `/transactions/${state.selectedTransactionId}`;
        }
    }

    // Add query parameters for context
    const params = new URLSearchParams();

    if (state.currentView !== 'account-list' && state.currentView !== 'account-detail' && !state.selectedFileId && !state.selectedTransactionId) {
        params.set('view', state.currentView);
    }

    if (state.context) {
        Object.entries(state.context).forEach(([key, value]) => {
            if (value) {
                params.set(key, value);
            }
        });
    }

    const queryString = params.toString();
    return queryString ? `${url}?${queryString}` : url;
};

// Create the session URL store
export const useSessionUrlStore = create<SessionUrlStore>()(
    persist(
        (set, get) => ({
            sessions: new Map(),

            generateSessionUrl: (navigationState: NavigationSessionState): string => {
                const traditionalUrl = generateTraditionalUrl(navigationState);

                // If URL is short enough, use traditional URL
                if (traditionalUrl.length <= MAX_URL_LENGTH) {
                    return traditionalUrl;
                }

                // Check if we already have a session for this state
                const stateHash = generateStateHash(navigationState);
                const existingSession = Array.from(get().sessions.values()).find(
                    session => generateStateHash(session.navigationState) === stateHash
                );

                if (existingSession) {
                    // Update access count and timestamp
                    const updatedSession = {
                        ...existingSession,
                        accessCount: existingSession.accessCount + 1,
                        lastAccessed: Date.now()
                    };

                    set(state => ({
                        sessions: new Map(state.sessions).set(existingSession.id, updatedSession)
                    }));

                    return `/accounts?s=${existingSession.id}`;
                }

                // Create new session
                const sessionId = generateSessionId();
                const newSession: SessionUrlEntry = {
                    id: sessionId,
                    url: traditionalUrl,
                    navigationState,
                    accessCount: 1,
                    lastAccessed: Date.now(),
                    created: Date.now()
                };

                set(state => {
                    const newSessions = new Map(state.sessions);
                    newSessions.set(sessionId, newSession);

                    // Clean up if we exceed max sessions
                    if (newSessions.size > MAX_SESSION_URLS) {
                        // Sort by LRU (least recently used + least accessed)
                        const sortedSessions = Array.from(newSessions.entries()).sort((a, b) => {
                            const scoreA = a[1].accessCount * 0.7 + (a[1].lastAccessed / 1000000) * 0.3;
                            const scoreB = b[1].accessCount * 0.7 + (b[1].lastAccessed / 1000000) * 0.3;
                            return scoreA - scoreB;
                        });

                        // Remove the least valuable sessions
                        const sessionsToRemove = sortedSessions.slice(0, newSessions.size - MAX_SESSION_URLS);
                        sessionsToRemove.forEach(([sessionId]) => {
                            newSessions.delete(sessionId);
                        });
                    }

                    return { sessions: newSessions };
                });

                return `/accounts?s=${sessionId}`;
            },

            resolveSessionUrl: (url: string): NavigationSessionState | null => {
                const urlObj = new URL(url, window.location.origin);
                const sessionId = urlObj.searchParams.get('s');

                if (!sessionId) {
                    return null;
                }

                const session = get().sessions.get(sessionId);
                if (!session) {
                    return null;
                }

                // Update access statistics
                const updatedSession = {
                    ...session,
                    accessCount: session.accessCount + 1,
                    lastAccessed: Date.now()
                };

                set(state => ({
                    sessions: new Map(state.sessions).set(sessionId, updatedSession)
                }));

                return session.navigationState;
            },

            getSessionEntry: (sessionId: string): SessionUrlEntry | null => {
                return get().sessions.get(sessionId) || null;
            },

            cleanupOldSessions: () => {
                const now = Date.now();
                const maxAge = 7 * 24 * 60 * 60 * 1000; // 7 days

                set(state => {
                    const newSessions = new Map();

                    for (const [id, session] of state.sessions) {
                        if (now - session.lastAccessed < maxAge) {
                            newSessions.set(id, session);
                        }
                    }

                    return { sessions: newSessions };
                });
            },

            clearAllSessions: () => {
                set({ sessions: new Map() });
            },

            isSessionUrl: (url: string): boolean => {
                try {
                    const urlObj = new URL(url, window.location.origin);
                    return urlObj.searchParams.has('s');
                } catch {
                    return false;
                }
            },

            getSessionStats: () => {
                const sessions = Array.from(get().sessions.values());

                if (sessions.length === 0) {
                    return {
                        totalSessions: 0,
                        oldestSession: 0,
                        newestSession: 0,
                        mostUsedSession: null
                    };
                }

                const sortedByAge = sessions.sort((a, b) => a.created - b.created);
                const sortedByUsage = sessions.sort((a, b) => b.accessCount - a.accessCount);

                return {
                    totalSessions: sessions.length,
                    oldestSession: sortedByAge[0].created,
                    newestSession: sortedByAge[sortedByAge.length - 1].created,
                    mostUsedSession: sortedByUsage[0]
                };
            }
        }),
        {
            name: 'session-url-store',
            // Only persist session data, not the Map itself
            partialize: (state) => ({
                sessions: Array.from(state.sessions.entries())
            }),
            // Restore the Map from persisted data
            onRehydrateStorage: () => (state) => {
                if (state && Array.isArray((state as any).sessions)) {
                    state.sessions = new Map((state as any).sessions);
                }
            }
        }
    )
);
