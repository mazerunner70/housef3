import { useState, FormEvent } from 'react';
import { useAuth } from '@/hooks/useAuth';
import './Login.css';

interface LoginProps {
    handleLogin: () => Promise<void>;
}

const Login = ({ handleLogin: onLoginCallback }: LoginProps) => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const { loginLoading, loginError, handleLogin: authHandleLogin } = useAuth();

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();

        if (!username || !password) {
            return;
        }

        // Call the auth hook's handleLogin to perform authentication
        // Note: authHandleLogin errors are handled internally by the useAuth hook
        await authHandleLogin(username, password);

        // On success, call the router's navigation callback (no sensitive data passed)
        try {
            await onLoginCallback();
        } catch (err) {
            console.error('Navigation callback error:', err);
        }
    };

    return (
        <div className="login-container">
            <form onSubmit={handleSubmit} className="login-form">
                <div className="form-group">
                    <label htmlFor="username">Username</label>
                    <input
                        type="text"
                        id="username"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        disabled={loginLoading}
                        required
                    />
                </div>

                <div className="form-group">
                    <label htmlFor="password">Password</label>
                    <input
                        type="password"
                        id="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        disabled={loginLoading}
                        required
                    />
                </div>

                {loginError && <div className="error-message">{loginError}</div>}

                <button type="submit" className="login-button" disabled={loginLoading}>
                    {loginLoading ? 'Signing in...' : 'Sign In'}
                </button>
            </form>
        </div>
    );
};

export default Login;

