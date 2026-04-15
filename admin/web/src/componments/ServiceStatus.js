import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Table, Tag,message } from 'antd';
import {
    checkAllServicesHealth
} from '../services/api';
import { emitRobotTalk } from '../utils/robotTalk';


const ServiceStatus = () => {
    const [data, setData] = useState([]);
    const [loading, setLoading] = useState(false);
    const [servicesData, setServicesData] = useState([]);
    const [tick, setTick] = useState(0);
    const prevUnhealthyRef = useRef(new Set());

    // 检查所有服务状态
    const checkAllServices = async () => {
        try {
            const result = await checkAllServicesHealth();
            console.log('所有服务检查结果:', result);
            
            const servicesList = [];
            for (const service of result.services) {
                if (service.status === 'success' && service.data && service.data.status === 'running') {
                    servicesList.push({
                        id: service.service,
                        service: service.service_name,
                        status: 1,
                        update_time: new Date().toISOString(),
                        health_data: service.data,
                        last_check: new Date().toISOString(),
                        loading: false
                    });
                } else {
                    servicesList.push({
                        id: service.service,
                        service: service.service_name,
                        status: 0,
                        update_time: new Date().toISOString(),
                        health_data: service.data || null,
                        last_check: new Date().toISOString(),
                        error: service.message || '服务异常',
                        loading: false
                    });
                }
            }
            
            setServicesData(servicesList);
            setData(servicesList);

            const unhealthyNames = servicesList
                .filter((item) => item.status === 0)
                .map((item) => item.service)
                .filter(Boolean);
            const nextSet = new Set(unhealthyNames);
            const prevSet = prevUnhealthyRef.current;
            let hasNew = false;
            for (const name of nextSet) {
                if (!prevSet.has(name)) {
                    hasNew = true;
                    break;
                }
            }
            if (hasNew && unhealthyNames.length > 0) {
                emitRobotTalk(`检测到服务异常：${unhealthyNames.join('、')}。`);
            }
            prevUnhealthyRef.current = nextSet;
        } catch (error) {
            emitRobotTalk('服务状态检查失败，请关注。');
            console.log('服务检查异常:', error);
            // 如果检查失败，显示默认的错误状态
            const defaultServices = [
                {
                    id: 'ASR',
                    service: '语音识别服务',
                    status: 0,
                    update_time: new Date().toISOString(),
                    health_data: null,
                    last_check: new Date().toISOString(),
                    error: '检查失败',
                    loading: false
                },
                {
                    id: 'TTS',
                    service: '语音合成服务',
                    status: 0,
                    update_time: new Date().toISOString(),
                    health_data: null,
                    last_check: new Date().toISOString(),
                    error: '检查失败',
                    loading: false
                },
                {
                    id: 'INTERACTION',
                    service: '交互服务',
                    status: 0,
                    update_time: new Date().toISOString(),
                    health_data: null,
                    last_check: new Date().toISOString(),
                    error: '检查失败',
                    loading: false
                }
            ];
            setServicesData(defaultServices);
            setData(defaultServices);
        }
    };

    useEffect(() => {
        fetchData();
        
        checkAllServices();

        const servicesIntervalId = setInterval(() => {
            checkAllServices();
        }, 300000);

        const tickIntervalId = setInterval(() => {
            setTick((prev) => prev + 1);
        }, 1000);

        return () => {
            clearInterval(servicesIntervalId);
            clearInterval(tickIntervalId);
        };
    }, []);

    useEffect(() => {
        if (servicesData.length > 0) {
            setData(servicesData);
        }
    }, [servicesData, tick]);

    const getUptimeSeconds = (record) => {
        if (!record.health_data || !record.health_data.uptime_seconds) {
            return null;
        }
        const base = Number(record.health_data.uptime_seconds);
        const lastCheck = record.last_check ? new Date(record.last_check).getTime() : Date.now();
        const delta = Math.max(0, Math.floor((Date.now() - lastCheck) / 1000));
        return base + delta;
    };

    function formatUptime(seconds) {
        if (seconds == null) {
            return '';
        }
        const total = Math.max(0, Math.floor(seconds));
        const h = Math.floor(total / 3600);
        const m = Math.floor((total % 3600) / 60);
        const s = total % 60;
        return `${h}时${m}分${s}秒`;
    }

    const fetchData = async (searchQuery = '') => {
        setLoading(true);
        try {
            if (servicesData.length > 0) {
                setData(servicesData);
            } else {
                // 显示默认的服务状态
                const defaultServices = [
                    {
                        id: 'ASR',
                        service: '语音识别服务',
                        status: 0,
                        update_time: new Date().toISOString(),
                        health_data: null,
                        last_check: new Date().toISOString(),
                        loading: false
                    },
                    {
                        id: 'TTS',
                        service: '语音合成服务',
                        status: 0,
                        update_time: new Date().toISOString(),
                        health_data: null,
                        last_check: new Date().toISOString(),
                        loading: false
                    },
                    {
                        id: 'INTERACTION',
                        service: '交互服务',
                        status: 0,
                        update_time: new Date().toISOString(),
                        health_data: null,
                        last_check: new Date().toISOString(),
                        loading: false
                    }
                ];
                setData(defaultServices);
            }
        } catch (error) {
            message.error('获取服务状态数据失败');
        } finally {
            setLoading(false);
        }
    };





    const formatDate = (date) => {
        return new Intl.DateTimeFormat('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        }).format(new Date(date));
    };

    const getStatusColor = (updateTime) => {
        const threeHundredSecondsAgo = new Date(new Date().setSeconds(new Date().getSeconds() - 300));
        const updateTimeDate = new Date(updateTime);

        if (updateTimeDate >= threeHundredSecondsAgo) {
            return 'green'; // 状态正常
        } else {
            return 'red'; // 状态异常
        }
    };

    const columns = [
        {
            title: 'ID',
            dataIndex: 'id',
            key: 'id',
        },
        {
            title: '服务',
            dataIndex: 'service',
            key: 'service',
        },
        {
            title: '状态',
            dataIndex: 'status',
            key: 'status',
            filters: [
                { text: '正常', value: '1' },
                { text: '异常', value: '0' },
            ],
            onFilter: (value, record) => record.status === value,
            render: (text, record) => {
                if (record.service === '语音识别服务' || record.service === '语音合成服务' || record.service === '交互服务') {
                    if (record.loading) {
                        return (
                            <div>
                                <Tag color="orange">检查中...</Tag>
                                <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>
                                    正在检查{record.service}状态
                                </div>
                            </div>
                        );
                    } else if (record.health_data) {
                        return (
                            <div>
                                <Tag color={getStatusColor(record.update_time)}>
                                    {text === 1 && getStatusColor(record.update_time) == 'green' ? '正常' : '异常'}
                                </Tag>
                                <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>
                                    {getUptimeSeconds(record) !== null && `运行: ${formatUptime(getUptimeSeconds(record))}`}
                                    {record.health_data.start_time && ` | 启动: ${new Date(record.health_data.start_time * 1000).toLocaleString()}`}
                                </div>
                            </div>
                        );
                    } else if (record.error) {
                        return (
                            <div>
                                <Tag color="red">异常</Tag>
                                <div style={{ fontSize: 12, color: '#ff4d4f', marginTop: 4 }}>
                                    错误: {record.error}
                                </div>
                            </div>
                        );
                    } else {
                        return (
                            <div>
                                <Tag color="red">未检查</Tag>
                                <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>
                                    正在检查{record.service}状态
                                </div>
                            </div>
                        );
                    }
                }
                return (
                    <Tag color={getStatusColor(record.update_time)}>
                        {text === 1 && getStatusColor(record.update_time) == 'green' ? '正常' : '异常'}
                    </Tag>
                );
            },
        },
        {
            title: '更新时间',
            dataIndex: 'update_time',
            key: 'update_time',
            render: (value) => formatDate(value),
        },
    ];

    return (
        <div className="app-page">
            <div className="app-panel">
                <Table
                    columns={columns}
                    dataSource={data}
                    rowKey="id"
                    loading={loading}
                    scroll={{ y: 640 }}
                />
            </div>
        </div>
    );
};

export default ServiceStatus;
