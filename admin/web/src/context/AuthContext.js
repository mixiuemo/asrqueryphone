// src/context/AuthContext.js
import React, { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true); // 添加加载状态

  // 初始化时从 localStorage 读取认证状态
  useEffect(() => {
    const storedUser = localStorage.getItem('user');
    const storedToken = localStorage.getItem('token');
    
    if (storedUser && storedToken) {
      const u = JSON.parse(storedUser);
      if (!Array.isArray(u.menu_paths)) {
        u.menu_paths = ['/tele'];
      }
      setUser(u);
      setIsAuthenticated(true);
    }
    setLoading(false);
  }, []);

  const login = (userData, token) => {
    const u = { ...userData };
    if (!Array.isArray(u.menu_paths)) {
      u.menu_paths = ['/tele'];
    }
    localStorage.setItem('user', JSON.stringify(u));
    localStorage.setItem('token', token ?? '');
    setUser(u);
    setIsAuthenticated(true);
  };

  const logout = () => {
    localStorage.removeItem('user');
    localStorage.removeItem('token');
    setUser(null);
    setIsAuthenticated(false);
  };

  

  // 如果正在加载，可以显示加载指示器
  if (loading) {
    return <div>Loading...</div>; // 或者你的自定义加载组件
  }

  return (
    <AuthContext.Provider value={{ user, isAuthenticated, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}