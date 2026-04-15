/**
 * 与后端 routes/role.py ALLOWED_MENU_PATHS 一致（增减菜单时需同步改后端）
 */
export const MENU_ITEMS = [
  { key: '1', path: '/tele', label: '通讯录', inSidebar: true },
  { key: '4', path: '/paraConfig', label: '参数设置', inSidebar: true },
  { key: '5', path: '/keywords', label: '热词配置', inSidebar: true },
  { key: '6', path: '/serviceStatus', label: '后台配置', inSidebar: true },
  { key: '7', path: '/users', label: '用户管理', inSidebar: true },
  { key: '12', path: '/mqtest', label: '交互逻辑测试', inSidebar: true },
  { key: '3', path: '/logs', label: '系统日志', inSidebar: true },
  // { key: 'train', path: '/trainConfig', label: '训练配置', inSidebar: false },
  // { key: 'wel', path: '/welConfig', label: '欢迎语配置', inSidebar: false },
];

export const SIDEBAR_ITEMS = MENU_ITEMS.filter((m) => m.inSidebar);

/** @param {string[]|undefined} menuPaths */
export function canAccessPath(pathname, menuPaths) {
  const paths = Array.isArray(menuPaths) && menuPaths.length ? menuPaths : ['/tele'];
  let p = pathname || '/';
  if (p !== '/' && p.endsWith('/')) p = p.slice(0, -1);
  if (p === '/') p = '/tele';
  return paths.includes(p);
}

export const FALLBACK_PATH = '/tele';
