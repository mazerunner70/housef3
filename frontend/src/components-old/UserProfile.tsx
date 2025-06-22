import { signOut, AuthUser } from '../services/AuthService';
import './UserProfile.css';

interface UserProfileProps {
  user: AuthUser;
  onSignOut: () => void;
}

const UserProfile = ({ user, onSignOut }: UserProfileProps) => {
  const handleSignOut = async () => {
    try {
      await signOut();
      onSignOut();
    } catch (error) {
      console.error('Error signing out:', error);
    }
  };

  const formatExpiryTime = (timestamp: number) => {
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  return (
    <div className="user-profile">
      <div className="user-info">
        <span className="username">{user.username}</span>
        {user.email && <span className="email">({user.email})</span>}
        <div className="token-expiry">
          Token expires: {formatExpiryTime(user.tokenExpiry)}
        </div>
      </div>
      <button className="sign-out-button" onClick={handleSignOut}>
        Sign Out
      </button>
    </div>
  );
};

export default UserProfile; 