import { AuthUser, signOut } from '../services/AuthService';
import './UserProfile.css';

interface UserProfileProps {
  user: AuthUser;
  onSignOut: () => void;
}

const UserProfile = ({ user, onSignOut }: UserProfileProps) => {
  const handleSignOut = async () => {
    await signOut();
    onSignOut();
  };

  return (
    <div className="user-profile">
      <div className="user-info">
        <h2>Hello, {user.username}!</h2>
        <p>Email: {user.email}</p>
      </div>
      <button className="sign-out-button" onClick={handleSignOut}>
        Sign Out
      </button>
    </div>
  );
};

export default UserProfile; 