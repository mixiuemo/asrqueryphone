import React, { useState, useEffect, useCallback } from 'react';
import {
  Table,
  Button,
  Space,
  Modal,
  Form,
  Input,
  message,
  Select,
  Tabs,
  Checkbox,
  Tag,
} from 'antd';
import { ExclamationCircleOutlined } from '@ant-design/icons';
import { debounce } from 'lodash';
import {
  getUsers,
  createUser,
  updateUser,
  deleteUser,
  getRoles,
  createRole,
  updateRole,
  deleteRole,
} from '../services/api';
import { MENU_ITEMS } from '../config/menuDefinitions';

const { Option } = Select;
const { confirm } = Modal;

function RoleMenuTab({ onRolesChanged }) {
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form] = Form.useForm();
  const [paths, setPaths] = useState({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getRoles();
      setRoles(Array.isArray(data) ? data : []);
    } catch (e) {
      message.error('加载角色失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    const init = {};
    MENU_ITEMS.forEach((m) => {
      init[m.path] = m.path === '/tele';
    });
    setPaths(init);
    setModalOpen(true);
  };

  const openEdit = (record) => {
    setEditing(record);
    form.setFieldsValue({
      role_code: record.role_code,
      role_name: record.role_name,
    });
    const init = {};
    MENU_ITEMS.forEach((m) => {
      init[m.path] = (record.menu_paths || []).includes(m.path);
    });
    setPaths(init);
    setModalOpen(true);
  };

  const togglePath = (path, checked) => {
    setPaths((p) => ({ ...p, [path]: checked }));
  };

  const submitRole = async () => {
    try {
      const values = await form.validateFields();
      const menu_paths = MENU_ITEMS.filter((m) => paths[m.path]).map((m) => m.path);
      if (!menu_paths.includes('/tele')) {
        message.error('须至少勾选「通讯录」/tele');
        return;
      }
      if (editing) {
        await updateRole(editing.role_code, {
          role_name: values.role_name,
          menu_paths,
        });
        message.success('角色已更新');
      } else {
        await createRole({
          role_code: values.role_code.trim().toLowerCase(),
          role_name: values.role_name.trim(),
          menu_paths,
        });
        message.success('角色已创建');
      }
      setModalOpen(false);
      await load();
      onRolesChanged?.();
    } catch (e) {
      if (e?.errorFields) return;
      message.error(e.response?.data?.error || e.message || '保存失败');
    }
  };

  const removeRole = (record) => {
    confirm({
      title: `删除角色「${record.role_name}」？`,
      icon: <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />,
      content: '若有用户绑定该角色将无法删除。',
      okType: 'danger',
      onOk: async () => {
        try {
          await deleteRole(record.role_code);
          message.success('已删除');
          await load();
          onRolesChanged?.();
        } catch (e) {
          message.error(e.response?.data?.error || '删除失败');
        }
      },
    });
  };

  const columns = [
    { title: '代码', dataIndex: 'role_code', key: 'role_code' },
    { title: '名称', dataIndex: 'role_name', key: 'role_name' },
    {
      title: '可访问页面',
      key: 'menu_paths',
      render: (_, r) => (
        <Space wrap size={[4, 4]}>
          {(r.menu_paths || []).map((p) => {
            const item = MENU_ITEMS.find((m) => m.path === p);
            return <Tag key={p}>{item ? item.label : p}</Tag>;
          })}
        </Space>
      ),
    },
    {
      title: '操作',
      key: 'op',
      width: 160,
      render: (_, r) => (
        <Space>
          <Button size="small" onClick={() => openEdit(r)}>
            编辑
          </Button>
          <Button size="small" danger onClick={() => removeRole(r)}>
            删除
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" onClick={openCreate}>
          新增角色
        </Button>
      </Space>
      <Table
        rowKey="role_code"
        loading={loading}
        columns={columns}
        dataSource={roles}
        pagination={false}
      />

      <Modal
        title={
          <div className="tele-modal-title">
            {editing ? '编辑角色' : '新增角色'}
          </div>
        }
        open={modalOpen}
        onOk={submitRole}
        onCancel={() => setModalOpen(false)}
        width={560}
        className="tele-modal"
        centered
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="role_code"
            label="角色代码（英文小写+下划线，唯一）"
            rules={[{ required: true, message: '必填' }]}
          >
            <Input disabled={!!editing} placeholder="如 auditor" />
          </Form.Item>
          <Form.Item
            name="role_name"
            label="角色名称"
            rules={[{ required: true, message: '必填' }]}
          >
            <Input placeholder="如 审计员" />
          </Form.Item>
        </Form>
        <div className="tele-modal-perms">
          <div className="tele-modal-section-title">菜单访问权限</div>
          <Space direction="vertical" size={10} style={{ width: '100%' }}>
            {MENU_ITEMS.map((m) => (
              <Checkbox
                key={m.path}
                checked={!!paths[m.path]}
                onChange={(e) => togglePath(m.path, e.target.checked)}
              >
                {m.label}{' '}
                <Tag>{m.path}</Tag>
                {!m.inSidebar ? <Tag color="default">仅路由</Tag> : null}
              </Checkbox>
            ))}
          </Space>
        </div>
      </Modal>
    </div>
  );
}

const PersonManagement = () => {
  const [data, setData] = useState([]);
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [form] = Form.useForm();
  const [searchQuery, setSearchQuery] = useState('');
  const [isPasswordVisible, setIsPasswordVisible] = useState(false);

  const fetchRoles = useCallback(async () => {
    try {
      const r = await getRoles();
      setRoles(Array.isArray(r) ? r : []);
    } catch {
      setRoles([]);
    }
  }, []);

  useEffect(() => {
    fetchData();
    fetchRoles();
  }, []);

  const fetchData = async (q = '') => {
    setLoading(true);
    try {
      const result = await getUsers(q);
      setData(result);
    } catch (error) {
      message.error('获取用户数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSearchChange = debounce((value) => {
    fetchData(value);
  }, 300);

  const handleSearch = () => {
    handleSearchChange(searchQuery);
  };

  const handleCreate = () => {
    form.resetFields();
    setEditingUser(null);
    setIsModalVisible(true);
    setIsPasswordVisible(true);
  };

  const handleEdit = (record) => {
    form.setFieldsValue(record);
    setEditingUser(record);
    setIsModalVisible(true);
    setIsPasswordVisible(false);
  };

  const handleDelete = async (employee_id) => {
    try {
      await deleteUser(employee_id);
      message.success('用户删除成功');
      fetchData(searchQuery);
    } catch (error) {
      message.error('用户删除失败');
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();

      if (editingUser) {
        if (!isPasswordVisible) {
          delete values.password;
        }
        await updateUser(editingUser.employee_id, values);
        message.success('用户信息更新成功');
      } else {
        await createUser(values);
        message.success('用户创建成功');
      }

      setIsModalVisible(false);
      fetchData(searchQuery);
    } catch (error) {
      if (error?.errorFields) return;
      message.error(error.response?.data?.error || '操作失败');
    }
  };

  const showDeleteConfirm = (employee_id, username) => {
    confirm({
      className: 'tele-confirm',
      title: '确定要删除这个用户吗？',
      icon: <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />,
      content: `即将删除用户 ${username} (ID: ${employee_id})`,
      okText: '确认删除',
      okType: 'danger',
      cancelText: '取消',
      centered: true,
      maskClosable: true,
      onOk() {
        return handleDelete(employee_id);
      },
    });
  };

  const roleFilters = roles.map((r) => ({
    text: `${r.role_name} (${r.role_code})`,
    value: r.role_code,
  }));

  const columns = [
    {
      title: '员工ID',
      dataIndex: 'employee_id',
      key: 'employee_id',
    },
    {
      title: '用户名',
      dataIndex: 'username',
      key: 'username',
    },
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      render: (role, record) =>
        record.role_name_display
          ? `${record.role_name_display} (${role})`
          : role,
      filters: roleFilters,
      onFilter: (value, record) => record.role === value,
    },
    {
      title: '部门',
      dataIndex: 'department',
      key: 'department',
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space size="middle">
          <Button onClick={() => handleEdit(record)}>编辑</Button>
          <Button
            danger
            onClick={() => showDeleteConfirm(record.employee_id, record.username)}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  const userTab = (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Input
          placeholder="搜索用户名、部门或员工ID"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onPressEnter={handleSearch}
          style={{ width: 300 }}
        />
        <Button type="primary" onClick={handleSearch}>
          搜索
        </Button>
        <Button type="primary" onClick={handleCreate} style={{ marginLeft: 16 }}>
          添加用户
        </Button>
      </Space>

      <Table
        columns={columns}
        dataSource={data}
        rowKey="employee_id"
        loading={loading}
        scroll={{ y: 640 }}
      />

      <Modal
        title={
          <div className="tele-modal-title">
            {editingUser ? '编辑用户信息' : '添加新用户'}
          </div>
        }
        open={isModalVisible}
        onOk={handleSubmit}
        onCancel={() => {
          setIsModalVisible(false);
          setIsPasswordVisible(false);
        }}
        width={600}
        className="tele-modal"
        centered
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="username"
            label="用户名"
            rules={[{ required: true, message: '请输入用户名!' }]}
          >
            <Input />
          </Form.Item>

          {(editingUser && isPasswordVisible) || !editingUser ? (
            <Form.Item
              name="password"
              label="密码"
              rules={[{ required: true, message: '请输入密码!' }]}
            >
              <Input.Password />
            </Form.Item>
          ) : null}

          {editingUser && (
            <Form.Item label="修改密码">
              <Button
                type=""
                style={{ background: '#409EFF' }}
                onClick={() => setIsPasswordVisible(!isPasswordVisible)}
              >
                {isPasswordVisible ? '取消修改密码' : '修改密码'}
              </Button>
            </Form.Item>
          )}

          <Form.Item
            name="employee_id"
            label="员工ID"
            rules={[{ required: true, message: '请输入员工ID!' }]}
          >
            <Input disabled={!!editingUser} />
          </Form.Item>

          <Form.Item
            name="role"
            label="角色"
            rules={[{ required: true, message: '请选择角色!' }]}
          >
            <Select placeholder="选择角色（来自 ai114_role）">
              {roles.map((r) => (
                <Option key={r.role_code} value={r.role_code}>
                  {r.role_name}（{r.role_code}）
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="department"
            label="部门"
            rules={[{ required: true, message: '请输入部门!' }]}
          >
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );

  return (
    <div className="app-page">
      <div className="app-panel">
        <Tabs
          defaultActiveKey="users"
          items={[
            { key: 'users', label: '用户账号', children: userTab },
            {
              key: 'roles',
              label: '角色与菜单权限',
              children: <RoleMenuTab onRolesChanged={fetchRoles} />,
            },
          ]}
        />
      </div>
    </div>
  );
};

export default PersonManagement;
