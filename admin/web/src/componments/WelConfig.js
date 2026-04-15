import React, { useState, useEffect } from 'react';
import { Table, Button, Space, Modal, Form, Input, message,Radio } from 'antd';
import { ExclamationCircleOutlined } from '@ant-design/icons';
import { getAllWelConfigs, getWelConfigById, createWelConfig, updateWelConfig, deleteWelConfig } from '../services/api'; // 确保路径正确
const { confirm } = Modal;

const WelConfig = () => {
  const [data, setData] = useState([]);
  const [processedDataSource, setProcessedDataSource] = useState([]);
  const [loading, setLoading] = useState(false);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [editingConfig, setEditingConfig] = useState(null);
  const [form] = Form.useForm();
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async (searchQuery = '') => {
    setLoading(true);
    try {
      const result = await getAllWelConfigs(searchQuery);
      setData(result);
      setProcessedDataSource(result.map((item, index) => ({
        ...item,
        displayId: index + 1,
      })));
    } catch (error) {
      message.error('获取欢迎配置失败');
      console.error(error); // 输出错误信息以便调试
    } finally {
      setLoading(false);
    }
  };

  const handleSearchChange = (value) => {
    if (typeof value === 'string') { // 确保 value 是字符串
      setSearchQuery(value);
      fetchData(value);
    } else {
      console.error('Invalid search query value:', value);
    }
  };

  const handleCreate = () => {
    form.resetFields(); // 重置表单字段
    setEditingConfig(null);
    setIsModalVisible(true);
  };

  const handleEdit = (record) => {
    form.setFieldsValue(record);
    setEditingConfig(record);
    setIsModalVisible(true);
  };

  const handleDelete = async (id) => {
    try {
      await deleteWelConfig(id);
      message.success('记录删除成功');
      fetchData();
    } catch (error) {
      message.error('记录删除失败');
      console.error(error); // 输出错误信息以便调试
    }
  };

  const showDeleteConfirm = (id) => {
    confirm({
      title: '确定要删除这条记录吗？',
      icon: <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />,
      content: `即将删除记录 ID: ${id}`,
      okText: '确认删除',
      okType: 'danger',
      cancelText: '取消',
      centered: true,
      maskClosable: true,
      onOk() {
        return handleDelete(id);
      }
    });
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (editingConfig) {
        await updateWelConfig(editingConfig.id, values);
        message.success('记录更新成功');
      } else {
        await createWelConfig(values);
        message.success('记录创建成功');
      }
      setIsModalVisible(false);
      fetchData();
    } catch (error) {
      message.error('操作失败');
      console.error(error); // 输出错误信息以便调试
    }
  };

  const columns = [
    {
      title: 'ID',
      dataIndex: 'displayId',
      key: 'displayId',
    },
    {
      title: '欢迎文本',
      dataIndex: 'text',
      key: 'text',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (text) => (text === 1 ? '启用' : '禁用'),
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space size="middle">
          <Button onClick={() => handleEdit(record)}>编辑</Button>
          <Button danger onClick={() => showDeleteConfirm(record.id)}>
            删除
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Input
          placeholder="搜索欢迎配置"
          value={searchQuery}
          onChange={(e) => handleSearchChange(e.target.value)}
          onPressEnter={() => fetchData(searchQuery)}
          style={{ width: 300 }}
        />
        <Button type="primary" onClick={() => fetchData(searchQuery)}>
          搜索功能
        </Button>
        <Button type="primary" onClick={handleCreate} style={{ marginLeft: 16 }}>
          添加欢迎配置
        </Button>
      </Space>

      <Table
        columns={columns}
        dataSource={processedDataSource}
        rowKey="id"
        loading={loading}
        scroll={{ x: 800, y: 640 }}
      />

      <Modal
        title={editingConfig ? '编辑欢迎配置' : '添加欢迎配置'}
        open={isModalVisible}
        onOk={handleSubmit}
        onCancel={() => {
          setIsModalVisible(false);
          form.resetFields(); // 关闭模态框时重置表单
        }}
        width={500}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="text"
            label="欢迎文本"
            rules={[{ required: true, message: '请输入欢迎文本!' }]}
          >
            <Input />
          </Form.Item>

          <Form.Item
            name="status"
            label="状态"
            rules={[{ required: true, message: '请选择状态!' }]}
            initialValue={1}
          >
            <Radio.Group>
              <Radio value={1}>启用</Radio>
              <Radio value={0}>禁用</Radio>
            </Radio.Group>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default WelConfig;