import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN'; // 引入中文语言包
import 'dayjs/locale/zh-cn'; // 日期组件需要额外配置
import App from './App';
import './index.css';
import './App.css';

const root = createRoot(document.getElementById('root'));
root.render(
  <StrictMode>
    <ConfigProvider locale={zhCN}>
    <App />
  </ConfigProvider>
  </StrictMode>
);