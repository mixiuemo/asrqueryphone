import React, { useState, useEffect } from 'react';
import { Table, Button, Space, Modal, Form, Input, message, Switch, Radio } from 'antd';
import { debounce } from 'lodash';
import {
    getParaConfig,
    createParaConfig,
    updateParaConfig,
} from '../services/api';

const PROTECTED_CONFIG_NAMES = new Set(['ai114_zrg', 'ai114_zj', 'ai114_unknown_policy']);

const UNKNOWN_POLICY_OPTIONS = [
    { label: '0 保守：仅查号，不转接', value: '0' },
    { label: '1 标准：查号且可转接（受转接总开关约束）', value: '1' },
    { label: '2 优先人工：直转人工（受转人工总开关约束）', value: '2' },
];

const CONFIG_SUCCESS_MESSAGE = {
    ai114_zrg: '转人工开关已更新',
    ai114_zj: '转接开关已更新',
    ai114_unknown_policy: '库外号码策略已更新',
};

const ParaConfig = () => {
    const [data, setData] = useState([]);
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
            const result = await getParaConfig(searchQuery);
            setData(result);
        } catch (error) {
            message.error('获取配置数据失败');
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
        setEditingConfig(null);
        setIsModalVisible(true);
    };

    const handleEdit = (record) => {
        form.setFieldsValue(record);
        setEditingConfig(record);
        setIsModalVisible(true);
    };

    const onChangeSwitch = async (checked, record) => {
        const payload = { ...record, value: checked ? '1' : '0' };
        try {
            await updateParaConfig(record.id, payload);
            message.success(CONFIG_SUCCESS_MESSAGE[record.name] || '配置项更新成功');
            fetchData();
        } catch (error) {
            message.error('配置项更新失败');
        }
    };

    const onChangeUnknownPolicy = async (val, record) => {
        const payload = { ...record, value: val };
        try {
            await updateParaConfig(record.id, payload);
            message.success('库外号码策略已更新');
            fetchData();
        } catch (error) {
            message.error(error.response?.data?.error || '更新失败');
        }
    };

    const handleSubmit = async () => {
        try {
            const values = await form.validateFields();
            if (editingConfig) {
                if (editingConfig.name === 'ai114_zrg' || editingConfig.name === 'ai114_zj') {
                    values.value = editingConfig.value;
                }
                await updateParaConfig(editingConfig.id, values);
                message.success(CONFIG_SUCCESS_MESSAGE[editingConfig.name] || '配置信息更新成功');
            } else {
                await createParaConfig(values);
                message.success('配置项创建成功');
            }

            setIsModalVisible(false);
            fetchData();
        } catch (error) {
            message.error(error.response?.data?.error || '操作失败');
        }
    };

    const renderValueCell = (_, record) => {
        if (record.name === 'ai114_zrg' || record.name === 'ai114_zj') {
            return (
                <Switch
                    checked={String(record.value) === '1'}
                    onChange={(checked) => onChangeSwitch(checked, record)}
                />
            );
        }
        if (record.name === 'ai114_unknown_policy') {
            const v = ['0', '1', '2'].includes(String(record.value))
                ? String(record.value)
                : '0';
            return (
                <Radio.Group
                    value={v}
                    onChange={(e) => onChangeUnknownPolicy(e.target.value, record)}
                    options={UNKNOWN_POLICY_OPTIONS}
                />
            );
        }
        return <span style={{ color: 'rgba(230, 237, 247, 0.9)' }}>{String(record.value ?? '')}</span>;
    };

    const columns = [
        {
            title: 'ID',
            dataIndex: 'id',
            key: 'id',
            width: 80,
        },
        {
            title: '配置名称',
            dataIndex: 'name',
            key: 'name',
            width: 220,
        },
        {
            title: '配置值',
            dataIndex: 'value',
            key: 'value',
            width: 420,
            render: renderValueCell,
        },
        {
            title: '描述',
            dataIndex: 'desc',
            key: 'desc',
        },
        {
            title: '操作',
            key: 'action',
            width: 120,
            fixed: 'right',
            render: (_, record) => (
                <Button onClick={() => handleEdit(record)}>编辑</Button>
            ),
        },
    ];

    return (
        <div className="app-page para-config-page">
            <div className="app-panel">
            <Space style={{ marginBottom: 16 }}>
                <Input
                    placeholder="搜索配置名称或 ID"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    onPressEnter={handleSearch}
                    style={{ width: 300 }}
                />
                <Button type="primary" onClick={handleCreate} className="para-config-value-btn" style={{ marginLeft: 16 }}>
                    添加新配置
                </Button>
            </Space>

            <Table
                columns={columns}
                dataSource={data}
                rowKey="id"
                loading={loading}
                scroll={{ x: 1100, y: 640 }}
            />

            <Modal
                title={(
                    <div className="tele-modal-title">
                        {editingConfig ? '编辑配置信息' : '添加新配置'}
                    </div>
                )}
                open={isModalVisible}
                onOk={handleSubmit}
                onCancel={() => setIsModalVisible(false)}
                width={600}
                className="tele-modal"
                centered
            >
                <Form form={form} layout="vertical">
                    <Form.Item
                        name="name"
                        label="配置名称"
                        rules={[{ required: true, message: '请输入配置名称!' }]}>
                        <Input disabled={!!editingConfig && PROTECTED_CONFIG_NAMES.has(editingConfig?.name)} />
                    </Form.Item>

                    <Form.Item
                        name="value"
                        label="配置值"
                        rules={[{ required: true, message: '请输入配置值!' }]}>
                        {editingConfig?.name === 'ai114_unknown_policy' ? (
                            <Radio.Group options={UNKNOWN_POLICY_OPTIONS} />
                        ) : (
                            <Input />
                        )}
                    </Form.Item>

                    <Form.Item
                        name="desc"
                        label="描述"
                        rules={[{ required: true, message: '请输入描述!' }]}>
                        <Input.TextArea rows={4} />
                    </Form.Item>
                </Form>
            </Modal>
            </div>
        </div>
    );
};

export default ParaConfig;
