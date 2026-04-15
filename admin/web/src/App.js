// src/App.js
import React from 'react';
import { BrowserRouter as Router, Route, Routes, Navigate } from 'react-router-dom';
import { Layout, Spin, Dropdown, Menu, Avatar, Button } from 'antd';
import { UserOutlined, LogoutOutlined } from '@ant-design/icons';
import SideMenu from './SideMenu';
import SideEmoRobot from './SideMenu/SideEmoRobot';
import MenuManagement from './MenuManagement';
import Login from './Login/Login';
import { AuthProvider, useAuth } from './context/AuthContext';
import ProtectedRoute from './componments/ProtectedRoute';
import config from './config';

const { Header, Content, Sider, Footer } = Layout;

function AppHeader() {
  const { user, logout } = useAuth();

  const menu = (
    <Menu>
      <Menu.Item key="logout" icon={<LogoutOutlined />} onClick={logout}>
        退出登录
      </Menu.Item>
    </Menu>
  );

  return (
    <Header className="custom-header">
      <div style={{ display: 'flex', alignItems: 'center' }}>
        <img
          src={require('./assets/image/logo.png')}
          style={{ width: 25, height: 25, marginRight: '10px' }}
        />
      </div>
      <div style={{ 
        display: 'flex', 
        // justifyContent: 'center', 
        alignItems: 'center', 
        flex: 1, 
        fontWeight: 500, 
        fontSize: '20px',
        color: '#fff',
      }}>
        {config.title}
      </div>
      <div style={{display:'flex'}}>
        <div style={{marginRight:30,color: '#fff',fontSize: '13px'}}>版本: {config.version}</div>
        <Dropdown overlay={menu} placement="bottomRight">
          <div style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
            <Avatar
              size="small"
              icon={<UserOutlined />}
              style={{ marginRight: 8 }}
            />
            <span style={{ color: '#fff',fontWeight:'bold',fontSize: '15px' }}>{user?.username || '用户'}</span>
          </div>
        </Dropdown>
      </div>
    </Header>
  );
}

function AppFooter() {
  return (
    <Footer style={{ textAlign: 'center', padding: '12px 16px', marginTop: 0, backgroundColor: 'transparent', boxShadow: 'none', color: 'rgba(230, 237, 247, 0.6)' }}>
      {config.title} ©2025 Created by XDG
    </Footer>
  );
}

function AppContent() {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', paddingTop: '64px' }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <Layout style={{ minHeight: '100vh', paddingTop: isAuthenticated ? '64px' : 0 }}>
      {isAuthenticated && (
        <Sider width={220} trigger={null} collapsible={false}>
          <SideMenu />
          <SideEmoRobot />
        </Sider>
      )}
      <Layout className="site-layout">
        {isAuthenticated && <AppHeader />}
        <Content style={{ margin: 0 }}>
          <div className="site-layout-background" style={{ padding: 0, minHeight: 'calc(100vh - 64px)' }}>
            <Routes>
              <Route path="/login" element={isAuthenticated ? <Navigate to="/" /> : <Login />} />
              <Route
                path="/*"
                element={
                  <ProtectedRoute>
                    <MenuManagement />
                  </ProtectedRoute>
                }
              />
            </Routes>
          </div>
        </Content>
        {isAuthenticated && <AppFooter />}
      </Layout>
    </Layout>
  );
}

function App() {
  return (
    <Router>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </Router>
  );
}

export default App;
