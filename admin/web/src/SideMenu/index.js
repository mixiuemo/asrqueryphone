import React from 'react';
import { Menu } from 'antd';
import { Link } from 'react-router-dom';
import {
  UserOutlined,
  DatabaseOutlined,
  ClockCircleOutlined,
  SettingOutlined,
  SearchOutlined,
  FireOutlined,
  MessageOutlined,
  RiseOutlined,
  SmileOutlined,
} from '@ant-design/icons';
import { useAuth } from '../context/AuthContext';
import { SIDEBAR_ITEMS } from '../config/menuDefinitions';

const MENU_ICONS = {
  1: DatabaseOutlined,
  4: SettingOutlined,
  5: FireOutlined,
  6: SearchOutlined,
  7: UserOutlined,
  12: MessageOutlined,
  3: ClockCircleOutlined,
  train: RiseOutlined,
  wel: SmileOutlined,
};

const SideMenu = () => {
  const { user } = useAuth();
  const allowed = new Set(user?.menu_paths || ['/tele']);
  const items = SIDEBAR_ITEMS.filter((m) => allowed.has(m.path));

  return (
    <div className="neo-menu-wrap">
      <Menu theme="dark" defaultSelectedKeys={['1']} mode="inline" className="neo-menu">
        {items.map((item) => {
          const Icon = MENU_ICONS[item.key];
          return (
            <Menu.Item key={item.key} icon={Icon ? <Icon /> : null}>
              <Link to={item.path}>{item.label}</Link>
            </Menu.Item>
          );
        })}
      </Menu>
    </div>
  );
};

export default SideMenu;
