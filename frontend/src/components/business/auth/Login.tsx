import { useState, FormEvent } from 'react';
import { useAuth } from '@/hooks/useAuth';
import './Login.css';

interface LoginProps {
    handleLogin: (username: string, password: string) => Promise<void>;
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

        try {
            // Call the auth hook's handleLogin to perform authentication
            await authHandleLogin(username, password);
            // On success, call the router's navigation callback
            await onLoginCallback(username, password);
        } catch (err) {
            // Error is handled by useAuth hook
            console.error('Login error:', err);
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

