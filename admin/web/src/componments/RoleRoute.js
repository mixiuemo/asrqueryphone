import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { canAccessPath, FALLBACK_PATH } from '../config/menuDefinitions';

export default function RoleRoute({ children }) {
  const { user } = useAuth();
  const { pathname } = useLocation();

  if (!canAccessPath(pathname, user?.menu_paths)) {
    return <Navigate to={FALLBACK_PATH} replace />;
  }

  return children;
}
