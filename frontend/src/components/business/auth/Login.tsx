import { useState, FormEvent } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { useNavigate } from 'react-router-dom';
import './Login.css';

interface LoginProps {
    onLoginSuccess?: () => void;
}

const Login = ({ onLoginSuccess }: LoginProps) => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const navigate = useNavigate();
    const { loginLoading, loginError, handleLogin: authHandleLogin } = useAuth();

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();

        if (!username || !password) {
            return;
        }

        try {
            // Perform authentication
            await authHandleLogin(username, password);

            // On success, call the callback or navigate to home
            if (onLoginSuccess) {
                onLoginSuccess();
            } else {
                navigate('/');
            }
        } catch (error) {
            // Error is already handled by useAuth hook (sets loginError state)
            console.error('Login failed:', error);
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

