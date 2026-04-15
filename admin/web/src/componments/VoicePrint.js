import React, { useState, useEffect } from 'react';
import { Table, Button, Space, Modal, Form, Input, message } from 'antd';
import { ExclamationCircleOutlined } from '@ant-design/icons';
import { getAllVoiceprintResults } from '../services/api'; // 确保路径正确
const { confirm } = Modal;

const VoicePrint = () => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [editingResult, setEditingResult] = useState(null);
  const [form] = Form.useForm();
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async (searchQuery = '') => {
    setLoading(true);
    try {
      const result = await getAllVoiceprintResults(searchQuery);
      setData(result);
    } catch (error) {
      message.error('获取声纹识别结果失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSearchChange = (value) => {
    if (typeof value === 'string') {
      setSearchQuery(value);
      fetchData(value);
    } else {
      console.error('Invalid search query value:', value);
    }
  };

  const handleCreate = () => {
    form.resetFields();
    setEditingResult(null);
    setIsModalVisible(true);
  };

  const handleEdit = (record) => {
    form.setFieldsValue(record);
    setEditingResult(record);
    setIsModalVisible(true);
  };

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
    },
    {
      title: '用户名',
      dataIndex: 'username',
      key: 'username',
    },
    {
      title: '相似度',
      dataIndex: 'max_cosine_similarity',
      key: 'max_cosine_similarity',
    },
    // {
    //   title: '特征值',
    //   dataIndex: 'embedding',
    //   key: 'embedding',
    // },
    {
      title: '电话号',
      dataIndex: 'phone',
      key: 'phone',
    },
    {
      title: '通道',
      dataIndex: 'channel',
      key: 'channel',
    },
    {
      title: '文件名',
      dataIndex: 'wav_file_name',
      key: 'wav_file_name',
    },
    {
      title: '当前时间',
      dataIndex: 'current_time',
      key: 'current_time',
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space size="middle">
          <Button onClick={() => handleEdit(record)}>查看详情</Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Input
          placeholder="搜索用户名或电话号码"
          value={searchQuery}
          onChange={(e) => handleSearchChange(e.target.value)}
          onPressEnter={() => fetchData(searchQuery)}
          style={{ width: 300 }}
        />
        <Button type="primary" onClick={() => fetchData(searchQuery)}>
          搜索
        </Button>
      </Space>

      <Table
        columns={columns}
        dataSource={data}
        rowKey="id"
        loading={loading}
        scroll={{ x: 1200, y: 640 }}
      />

      <Modal
        title={'声纹识别日志'}
        open={isModalVisible}
        onOk={() => {
          form.validateFields()
            .then(() => {
              setIsModalVisible(false);
              form.resetFields();
            })
            .catch((info) => {
              console.log('Validate Failed:', info);
            });
        }}
        onCancel={() => {
          setIsModalVisible(false);
          form.resetFields();
        }}
        width={700}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="username"
            label="用户名"
            rules={[{ required: true, message: '请输入用户名!' }]}
          >
            <Input readOnly/>
          </Form.Item>

          <Form.Item
            name="max_cosine_similarity"
            label="相似度"
            rules={[{ required: true, message: '请输入相似度!' }]}
          >
            <Input type="number" readOnly/>
          </Form.Item>

          <Form.Item
            name="embedding"
            label="特征值"
            rules={[{ required: true, message: '请输入特征值!' }]}
          >
            <Input.TextArea rows={4} readOnly/>
          </Form.Item>

          <Form.Item
            name="phone"
            label="电话号"
            rules={[{ required: true, message: '请输入电话号!' }]}
          >
            <Input readOnly/>
          </Form.Item>

          <Form.Item
            name="channel"
            label="通道"
            rules={[{ required: true, message: '请输入通道!' }]}
          >
            <Input readOnly/>
          </Form.Item>

          <Form.Item
            name="wav_file_name"
            label="文件名"
            rules={[{ required: true, message: '请输入文件名!' }]}
          >
            <Input readOnly/>
          </Form.Item>

          <Form.Item
            name="current_time"
            label="当前时间"
            rules={[{ required: true, message: '请输入当前时间!' }]}
          >
            <Input readOnly/>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default VoicePrint;