import React, { useState } from 'react';
import { Button, Form, Input, message, Modal } from 'antd';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { getloginer, createUser } from '../services/api';
import './Login.css';

const Login = () => {
  const [loading, setLoading] = useState(false);
  const [registerLoading, setRegisterLoading] = useState(false);
  const [registerVisible, setRegisterVisible] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const renderMeteors = () => {
    return Array.from({ length: 10 }).map((_, i) => (
      <div 
        key={i} 
        className="meteor" 
        style={{
          left: `${Math.random() * 100}vw`,
          animationDuration: `${Math.random() * 2 + 3}s`,
          animationDelay: `${Math.random() * 5}s`
        }}
      />
    ));
  };

  const onFinish = async (values) => {
    setLoading(true);
    try {
      const result = await getloginer(values);
      const { user, token } = result;
      login(user, token);
      message.success('登录成功');
      navigate('/');
    } catch (error) {
      message.error('登录失败: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const onRegisterFinish = async (values) => {
    setRegisterLoading(true);
    try {
      await createUser(values);
      message.success('注册申请已发送，请联系管理员审核');
      setRegisterVisible(false);
    } catch (error) {
      message.error('申请提交失败: ' + error.message);
    } finally {
      setRegisterLoading(false);
    }
  };

  return (
    <div className="login-page-xdg">
      {renderMeteors()}

      {/* 左侧容器：增加 dynamic-width 动画类 */}
      <div className="left-panel-xdg dynamic-width">
        <div className="xdg-container">
          <div className="letter l-1">X</div>
          <div className="letter l-2">I</div>
          <div className="letter l-3">D</div>
          <div className="letter l-4">I</div>
          <div className="letter l-5">G</div>
          <div className="letter l-symbol">
            <svg viewBox="0 0 100 100" className="symbol-svg">
              <circle cx="50" cy="50" r="35" fill="none" stroke="currentColor" strokeWidth="2" opacity="0.8"/>
              <ellipse cx="50" cy="50" rx="35" ry="12" fill="none" stroke="currentColor" strokeWidth="1" opacity="0.5"/>
              <ellipse cx="50" cy="50" rx="12" ry="35" fill="none" stroke="currentColor" strokeWidth="1" opacity="0.5"/>
              <ellipse cx="50" cy="50" rx="48" ry="15" fill="none" stroke="#FFD700" strokeWidth="3" transform="rotate(-35 50 50)" className="orbit-line"/>
              <text x="50" y="62" textAnchor="middle" fontSize="32" fill="currentColor" fontStyle="italic" fontWeight="bold">e</text>
            </svg>
          </div>
        </div>

        <div className="ai-avatar-xdg">
          <div className="robot-head-xdg">
            <div className="robot-eyes-xdg">
              <div className="eye-xdg"></div>
              <div className="eye-xdg"></div>
            </div>
          </div>
        </div>
        
        <div className="brand-info-xdg">
          <h1>智能114转接平台</h1>
          <p></p>
        </div>

        <div className="wave-container-xdg">
          <svg className="wave-svg" viewBox="0 0 1200 120" preserveAspectRatio="none">
            <defs>
              <linearGradient id="wave-gradient" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stopColor="#00f2fe" stopOpacity="0.8" />
                <stop offset="100%" stopColor="#05080c" stopOpacity="0" />
              </linearGradient>
            </defs>
            <path className="wave-path" d="M0,60 C150,110 300,10 450,60 C600,110 750,10 900,60 C1050,110 1200,10 1350,60 L1350,120 L0,120 Z" />
          </svg>
        </div>
      </div>

      {/* 右侧面板 */}
      <div className="right-panel-xdg panel-entry">
        <div className="login-box-xdg">
          <div className="login-inner-xdg">
            <h2 className="xdg-title">控制中心登录</h2>
            <Form name="login" onFinish={onFinish} layout="vertical">
              <Form.Item name="username" label={<span className="xdg-label">账号</span>} rules={[{ required: true }]}>
                <Input placeholder="系统账号" className="xdg-input" />
              </Form.Item>
              <Form.Item name="password" label={<span className="xdg-label">密码</span>} rules={[{ required: true }]}>
                <Input.Password placeholder="系统密码" className="xdg-input" />
              </Form.Item>
              <Form.Item>
                <Button type="primary" htmlType="submit" loading={loading} className="xdg-btn-submit">
                  <span>启 动 系 统</span>
                </Button>
              </Form.Item>
              {/* <div className="xdg-footer">
                <Button type="link" onClick={() => setRegisterVisible(true)} className="xdg-link">
                  权限申请入口
                </Button>
              </div> */}
            </Form>
          </div>
        </div>
      </div>

      <Modal
        title={null}
        open={registerVisible}
        onCancel={() => setRegisterVisible(false)}
        footer={null}
        centered
        width={450}
        className="xdg-modal"
        destroyOnClose
      >
        <div className="modal-glow-container">
          <div className="login-inner-xdg">
            <h2 className="xdg-title" style={{ fontSize: '24px' }}>用户权限申请</h2>
            <Form name="register" onFinish={onRegisterFinish} layout="vertical">
              <Form.Item name="username" label={<span className="xdg-label">用户名</span>} rules={[{ required: true }]}>
                <Input className="xdg-input" placeholder="输入识别名" />
              </Form.Item>
              <Form.Item name="password" label={<span className="xdg-label">访问密码</span>} rules={[{ required: true }]}>
                <Input.Password className="xdg-input" placeholder="设置加密密钥" />
              </Form.Item>
              <Form.Item name="employee_id" label={<span className="xdg-label">员工ID</span>} rules={[{ required: true }]}>
                <Input className="xdg-input" placeholder="系统唯一标识码" />
              </Form.Item>
              <div style={{ display: 'flex', gap: '15px' }}>
                <Form.Item name="role" label={<span className="xdg-label">角色</span>} style={{ flex: 1 }}>
                  <Input className="xdg-input" placeholder="权限组" />
                </Form.Item>
                <Form.Item name="department" label={<span className="xdg-label">部门</span>} style={{ flex: 1 }}>
                  <Input className="xdg-input" placeholder="所属科室" />
                </Form.Item>
              </div>
              <Form.Item style={{ marginBottom: 0 }}>
                <Button type="primary" htmlType="submit" loading={registerLoading} className="xdg-btn-submit">
                  <span>提 交 申 请</span>
                </Button>
              </Form.Item>
            </Form>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default Login;


