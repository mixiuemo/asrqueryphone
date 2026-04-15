import React, { useState, useEffect } from 'react';
import { Table, Button, Space, Modal, Form, Input, message, Upload, Select, Tooltip } from 'antd';
import { ExclamationCircleOutlined, UploadOutlined, DownloadOutlined } from '@ant-design/icons';
import { debounce } from 'lodash';
import { getTeleData, createTele, updateTele, deleteTele, importTeleData, updatepinyintele, writeDataToJson, updateUserPermissionInJson, clearAllTeleData } from '../services/api';
import { emitRobotTalk } from '../utils/robotTalk';

const { confirm } = Modal;
const API_BASE_URL = 'http://localhost:5000/api';

const TeleManagement = () => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [editingTele, setEditingTele] = useState(null);
  const [form] = Form.useForm();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRowKeys, setSelectedRowKeys] = useState([]); // 选中的行的键值
  const [selectedRows, setSelectedRows] = useState([]); // 选中的行数据
  const [updatingPermissions, setUpdatingPermissions] = useState(new Set()); // 正在更新的权限记录

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async (searchQuery = '') => {
    setLoading(true);
    try {
      const result = await getTeleData(searchQuery);
      setData(result);
    } catch (error) {
      message.error('数据库连接失败');
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
    setEditingTele(null);
    setIsModalVisible(true);
  };

  const handlepinyin =async () => {
    setLoading(true);
    console.log('拼音转换');
    const result = await updatepinyintele();
    if (result.status === 200) {
      message.success('拼音转换成功');
    } else {
      message.error('拼音转换失败');
    }
    setLoading(false);
  };

  const handleWriteData = async () => {
    setLoading(true);
    console.log('数据写入');
    try {
      const result = await writeDataToJson();
      if (result.status === 200) {
        message.success(`数据写入成功！生成了${result.details.total_templates}个查询模板和${result.details.total_users}个用户详细信息`);
        emitRobotTalk('模板写入成功，我已经准备好了。');
      } else {
        message.error('数据写入失败');
      }
    } catch (error) {
      message.error('数据写入失败：' + error.message);
    }
    setLoading(false);
  };

  const onChangeLevel = async (level, record) => {
    const recordKey = record.NUMBER;
    
    setUpdatingPermissions(prev => new Set(prev).add(recordKey));
    
    try {
      await updateTele(record.NUMBER, { queryPermission: level });
      
      setData(prevData => 
        prevData.map(item => 
          item.NUMBER === record.NUMBER 
            ? { ...item, queryPermission: level }
            : item
        )
      );
      
      try {
        await updateUserPermissionInJson(record.NUMBER, level);
        console.log('JSON文件中的用户权限已更新');
      } catch (jsonError) {
        console.error('更新JSON文件中的用户权限失败:', jsonError);
      }
      
      message.success('等级更新成功');
    } catch (error) {
      message.error('等级更新失败');
    } finally {
      // 从更新中的记录集合移除
      setUpdatingPermissions(prev => {
        const newSet = new Set(prev);
        newSet.delete(recordKey);
        return newSet;
      });
    }
  };

  const handleEdit = (record) => {
    form.setFieldsValue(record);
    setEditingTele(record);
    setIsModalVisible(true);
  };

  // 监听姓名变化，自动更新姓氏
  const handlePersonnelChange = (e) => {
    const personnel = e.target.value;
    const surname = personnel ? personnel[0] : '';
    form.setFieldsValue({ surname });
  };

  const handleDelete = async (id) => {
    try {
      await deleteTele(id);
      message.success('数据删除成功');
      fetchData();
    } catch (error) {
      message.error('数据删除失败');
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();

      if (editingTele) {
        await updateTele(editingTele.NUMBER, values);
        message.success('修改数据成功');
      } else {
        await createTele(values);
        message.success('新增数据成功');
      }

      setIsModalVisible(false);
      fetchData();
    } catch (error) {
      message.error('操作失败');
    }
  };

  // 确认删除
  const showDeleteConfirm = (number) => {
    confirm({
      className: 'tele-confirm',
      title: '确定要删除这条记录吗？',
      icon: <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />,
      content: `即将删除编号 ${number} 的记录`,
      okText: '确认删除',
      okType: 'danger',
      cancelText: '取消',
      centered: true,
      maskClosable: true,
      onOk() {
        return handleDelete(number);
      }
    });
  };

  // 批量删除
  const handleBatchDelete = () => {
    if (selectedRows.length === 0) {
      message.warning('请至少选择一条记录进行删除');
      return;
    }

    confirm({
      className: 'tele-confirm',
      title: '确定要删除选中的记录吗？',
      icon: <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />,
      content: `即将删除 ${selectedRows.length} 条记录`,
      okText: '确认删除',
      okType: 'danger',
      cancelText: '取消',
      centered: true,
      maskClosable: true,
      onOk: async () => {
        try {
          const ids = selectedRows.map(row => row.NUMBER);
          await Promise.all(ids.map(id => deleteTele(id)));
          message.success('批量删除成功');
          setSelectedRowKeys([]);
          setSelectedRows([]);
          fetchData();
        } catch (error) {
          message.error('批量删除失败');
        }
      }
    });
  };

  const handleClearAll = async () => {
    try {
      setLoading(true);
      const result = await clearAllTeleData();
      message.success(result?.message || '清空成功');
      setSelectedRowKeys([]);
      setSelectedRows([]);
      fetchData();
    } catch (error) {
      message.error(error.response?.data?.error || '清空失败');
    } finally {
      setLoading(false);
    }
  };

  const showClearAllConfirm = () => {
    confirm({
      className: 'tele-clear-confirm',
      title: '危险操作：清空通讯录',
      icon: <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />,
      content: (
        <div className="tele-clear-confirm__content">
          <div className="tele-clear-confirm__tag">DANGER ZONE</div>
          <div className="tele-clear-confirm__text">将删除通讯录表中全部记录，且无法恢复。</div>
        </div>
      ),
      okText: '确认清空',
      okType: 'danger',
      cancelText: '取消',
      centered: true,
      maskClosable: true,
      onOk() {
        return handleClearAll();
      }
    });
  };

  // 在组件中添加下载方法
  const downloadTemplate = () => {
    const link = document.createElement('a');
    link.href = `${API_BASE_URL}/tele/template`;
    link.download = 'tele_template.xlsx';
    link.style.display = 'none';
    link.setAttribute('Authorization', `Bearer ${localStorage.getItem('token')}`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // 批量导入
  const handleImport = async (info) => {
    if (info.file.status === 'done') {
      message.success(`成功导入 ${info.file.response.imported} 条数据`);
      emitRobotTalk(`导入完成，共 ${info.file.response.imported} 条。`);
      message.info('请依次点击“拼音转换”和“数据写入”完成模板更新');
      fetchData();
    } else if (info.file.status === 'error') {
      message.error(info.file.response?.message || '导入失败');
    }
  };

  const columns = [
    {
      title: '编号',
      dataIndex: 'NUMBER',
      key: 'NUMBER',
      width: 90,
      sorter: (a, b) => a.NUMBER - b.NUMBER,
    },
    {
      title: '电话类型',
      dataIndex: 'telephoneType',
      key: 'telephoneType',
      width: 120,
      ellipsis: true,
      render: (value, record) => {
        return record.telephoneType || record.DEPARTMENT || '';
      }
    },
    {
      title: '人员',
      dataIndex: 'PERSONNEL',
      key: 'PERSONNEL',
      width: 140,
      ellipsis: true,
    },
    {
      title: '电话号码',
      dataIndex: 'TELE_CODE',
      key: 'TELE_CODE',
      width: 120,
    },
    {
      title: '职位',
      dataIndex: 'JOB',
      key: 'JOB',
      width: 80,
      ellipsis: true,
    },
    {
      title: '单位',
      dataIndex: 'UNIT',
      key: 'UNIT',
      ellipsis: true,
      render: (value) => (
        <Tooltip title={value || ''}>
          <span>{value}</span>
        </Tooltip>
      )
    },
    {
      title: '单位简称',
      dataIndex: 'unitAbbreviation',
      key: 'unitAbbreviation',
      ellipsis: true,
      render: (value) => (
        <Tooltip title={value || ''}>
          <span>{value}</span>
        </Tooltip>
      )
    },
    {
      title: '等级限制',
      dataIndex: 'queryPermission',
      key: 'queryPermission',
      width: 120,
      render: (value, record) => {
        const isUpdating = updatingPermissions.has(record.NUMBER);
        return (
          <div>
            <Select
              value={record.queryPermission ?? 1}
              style={{ width: 100 }}
              onChange={(level) => onChangeLevel(level, record)}
              loading={isUpdating}
              disabled={isUpdating}
              options={[
                { value: 1, label: '1级' },
                { value: 2, label: '2级' },
                { value: 3, label: '3级' },
              ]}
            />
          </div>
        );
      }
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space size="middle">
          <Button onClick={() => handleEdit(record)}>编辑</Button>
          <Button danger onClick={() => showDeleteConfirm(record.NUMBER)}>删除</Button>
        </Space>
      ),
    },
  ];

  return (
    <div className="app-page">
      <div className="app-panel">
      <Space style={{ marginBottom: 16 }}>
        <Input
          placeholder="搜索用户或电话号码"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onPressEnter={handleSearch}
          style={{ width: 300 }}
        />
        <Button type="primary" onClick={handleSearch}>
          搜索框
        </Button>
        <Button type="primary" onClick={handleCreate} style={{ marginLeft: 16 }}>
          添加通讯数据
        </Button>
        <Button type="primary" onClick={handlepinyin} style={{ marginLeft: 16 }}>
          拼音转换
        </Button>
        <Button type="primary" onClick={handleWriteData} style={{ marginLeft: 16 }}>
          数据写入
        </Button>
        <Upload
          name="file"
          accept=".xls,.xlsx"
          action={`${API_BASE_URL}/tele/importtele`}
          headers={{
            Authorization: `Bearer ${localStorage.getItem('token')}`
          }}
          beforeUpload={(file) => {
            const isExcel = ['xls', 'xlsx'].includes(
              file.name.split('.').pop().toLowerCase()
            );
            if (!isExcel) {
              message.error('仅支持Excel文件!');
              return false;
            }
            return true;
          }}
          onChange={handleImport}
          showUploadList={false}
        >
          <Button type="primary" style={{ marginLeft: 16 }}>
            批量导入
          </Button>
        </Upload>
        <Button
          type="default"
          icon={<DownloadOutlined />}
          onClick={downloadTemplate}
          style={{ marginLeft: 16 }}
        >
          下载模板
        </Button>
        <Button
          type="primary"
          danger
          onClick={handleBatchDelete}
          disabled={selectedRows.length === 0}
          style={{ marginLeft: 16 }}
        >
          批量删除
        </Button>
        <Button
          type="primary"
          danger
          onClick={showClearAllConfirm}
          style={{ marginLeft: 16 }}
        >
          一键清空
        </Button>
      </Space>

      <Table
        columns={columns}
        dataSource={data}
        rowKey="NUMBER"
        loading={loading}
        scroll={{ y: 640 }}
        rowSelection={{
          selectedRowKeys,
          onChange: (selectedRowKeys, selectedRows) => {
            setSelectedRowKeys(selectedRowKeys);
            setSelectedRows(selectedRows);
          }
        }}
      />

      <Modal
        title={(
          <div className="tele-modal-title">
            {editingTele ? '编辑通讯数据' : '添加通讯数据'}
          </div>
        )}
        open={isModalVisible}
        onOk={handleSubmit}
        onCancel={() => setIsModalVisible(false)}
        width={800}
        className="tele-modal"
        centered
      >
        <Form form={form} layout="vertical">
          <div className="tele-modal-grid">
            <Form.Item
              name="PERSONNEL"
              label="姓名"
              rules={[{ required: true, message: '请输入姓名!' }]}
            >
              <Input onChange={handlePersonnelChange} />
            </Form.Item>
            <Form.Item
              name="surname"
              label="姓氏"
            >
              <Input placeholder="自动从姓名提取，可手动修改" />
            </Form.Item>
            <Form.Item
              name="TELE_CODE"
              label="电话号码"
              rules={[{ required: true, message: '请输入电话号码!' }]}
            >
              <Input />
            </Form.Item>
            <Form.Item
              name="telephoneType"
              label="电话类型"
            >
              <Input />
            </Form.Item>

            <Form.Item
              name="UNIT"
              label="单位"
            >
              <Input />
            </Form.Item>
            <Form.Item
              name="unitAbbreviation"
              label="单位简称"
            >
              <Input />
            </Form.Item>
            <Form.Item
              name="JOB"
              label="职位"
            >
              <Input />
            </Form.Item>
          </div>
          <div style={{ marginTop: 16 }}>
            <Form.Item
              name="queryPermission"
              label="等级限制"
              initialValue={1}
            >
              <Select
                options={[
                  { value: 1, label: '1级' },
                  { value: 2, label: '2级' },
                  { value: 3, label: '3级' },
                ]}
              />
            </Form.Item>
          </div>
        </Form>
      </Modal>
      </div>
    </div>
  );
};

export default TeleManagement;
