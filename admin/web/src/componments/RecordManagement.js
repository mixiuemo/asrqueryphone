import React, { useState, useEffect } from 'react';
import { Table, Button, Space, Modal, Form, Input, message, Select, Tag } from 'antd';
import { debounce } from 'lodash';
import {
  getLogs,
  createLogs,
  updateLogs,
  deleteLogs
} from '../services/api';

const { TextArea } = Input;
const { Option } = Select;

const RecordManagement = () => {
  const [data, setData] = useState([]);
  const [filteredData, setFilteredData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [form] = Form.useForm();
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async (searchQuery = '') => {
    setLoading(true);
    try {
      const result = await getLogs(searchQuery); // 传递搜索关键词
      setData(result);
      setFilteredData(result); // 初始化时显示所有数据
    } catch (error) {
      message.error('获取用户数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSearchChange = debounce((value) => {
    fetchData(value);
  }, 300); // 防抖时间设置为 300ms

  const handleCreate = () => {
    form.resetFields();
    setEditingUser(null);
    setIsModalVisible(true);
  };

  const handleEdit = (record) => {
    const formData = {
      ...record,
      userResult: record.userResult || '',
      sysResult: record.sysResult || '',
      wavFileName: record.wavFileName || '',
      syswavFileName: record.syswavFileName || '',
      isDelete: record.isDelete || 0
    };
    form.setFieldsValue(formData);
    setIsModalVisible(true);
  };

  const handleDelete = async (id) => {
    try {
      await deleteLogs(id);
      message.success('删除成功');
      fetchData();
    } catch (error) {
      message.error('删除失败');
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (editingUser) {
        await updateLogs(editingUser.id, values);
        message.success('更新成功');
      } else {
        await createLogs(values);
        message.success('创建成功');
      }
      setIsModalVisible(false);
      fetchData();
    } catch (error) {
      message.error('操作失败');
    }
  };

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
      sorter: (a, b) => a.id - b.id,
    },
    {
      title: '用户查询',
      dataIndex: 'userResult',
      key: 'userResult',
      render: (text) => (
        <div style={{ maxWidth: 200, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {text?.replace(/##/g, '')}
        </div>
      ),
    },
    {
      title: '系统回复',
      dataIndex: 'sysResult',
      key: 'sysResult',
      render: (text) => (
        <div style={{ maxWidth: 200, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {text?.replace(/##/g, '')}
        </div>
      ),
    },
    {
      title: '录音文件',
      dataIndex: 'wavFileName',
      key: 'wavFileName',
      render: (text) => (
        <div style={{ maxWidth: 200, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {text?.replace(/##/g, '')}
        </div>
      ),
    },
    {
      title: '时间',
      dataIndex: 'resultTime',
      key: 'resultTime',
      render: (text) => new Date(text).toLocaleString(),
      sorter: (a, b) => new Date(a.resultTime) - new Date(b.resultTime),
    },
    {
      title: '状态',
      dataIndex: 'isDelete',
      key: 'isDelete',
      render: (isDelete) => (
        <Tag color={isDelete === 0 ? 'green' : 'red'}>
          {isDelete === 0 ? '正常' : '已删除'}
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_, record) => (
        <Space size="middle">
          <Button onClick={() => handleEdit(record)}>详情</Button>
          {/* <Button danger onClick={() => handleDelete(record.id)}>删除</Button> */}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Input
        placeholder="搜索用户查询内容或系统回复内容"
        value={searchQuery}
        onChange={(e) => {
          setSearchQuery(e.target.value);
          handleSearchChange(e.target.value);
        }}
        style={{ marginBottom: 16, width: 300 }}
      />

      <Table
        columns={columns}
        dataSource={filteredData}
        rowKey="id"
        loading={loading}
        // scroll={{ x: 1500 }}
        scroll={{ x: 1500, y: 640 }} // 设置表格的最大高度为 300px，并添加垂直滚动条[^19^]
        bordered
      />

      <Modal
        title={editingUser ? '查看详情' : '查看详情'}
        open={isModalVisible}
        onOk={() => setIsModalVisible(false)}
        onCancel={() => setIsModalVisible(false)}
        width={800}
        destroyOnClose={false}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="id" label="ID" hidden>
            <Input />
          </Form.Item>

          <Form.Item
            name="userResult"
            label="用户查询"
            rules={[{ required: true, message: '请输入用户查询内容!' }]}
          >
            <TextArea rows={2} />
          </Form.Item>

          <Form.Item
            name="sysResult"
            label="系统回复"
            rules={[{ required: true, message: '请输入系统回复内容!' }]}
          >
            <TextArea rows={3} />
          </Form.Item>

          <Form.Item
            name="wavFileName"
            label="录音文件名"
          >
            <Input />
          </Form.Item>

          <Form.Item
            name="syswavFileName"
            label="系统录音文件名"
          >
            <Input />
          </Form.Item>

          <Form.Item
            name="resultTime"
            label="结果时间"
          >
            <Input disabled />
          </Form.Item>

          <Form.Item
            name="isDelete"
            label="状态"
          >
            <Select>
              <Option value={0}>正常</Option>
              <Option value={1}>已删除</Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default RecordManagement;