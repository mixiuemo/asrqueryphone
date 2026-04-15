import React, { useState, useEffect } from 'react';
import { Table, Select, Modal, message, Button, Tooltip, DatePicker, Card, Space, Input, Tag, Row, Col, Statistic } from 'antd';
import { SearchOutlined, EyeOutlined, CalendarOutlined, PhoneOutlined, UserOutlined, AudioOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import './Auto114result.css'
import {
    getLogs,
    createLogs,
    updateLogs,
    deleteLogs
} from '../services/api';
import config from '../config';
var moment = require('moment');

const Auto114Result = (props) => {
    const navigate = useNavigate();

    const [dataSource, setDataSource] = useState([]);
    const [data, setData] = useState({});
    const [visible, setVisible] = useState(false);
    const [pageSize, setPageSize] = useState(10);
    const [page, setPage] = useState(1);
    const [total, setTotal] = useState(0);
    const [selectedRow, setSelectedRow] = useState([]);
    const [recordTime, setRecordTime] = useState("");
    const [searchStartDate, setSearchStartDate] = useState(null);
    const [searchEndDate, setSearchEndDate] = useState(null);
    const [searchStatus, setSearchStatus] = useState(0);
    const [channelNumber, setChannelNumber] = useState("-1");
    const [selectedRowKeys, setSelectedRowKeys] = useState([]);

    useEffect(() => {
        fetchLogs();
    }, [page, pageSize]);

    const fetchLogs = async () => {
        try {
            const response = await getLogs(searchStartDate, searchEndDate);
            setDataSource(response);
            setTotal(response.length);
        } catch (error) {
            console.error('Error fetching logs:', error);
            message.error('获取日志失败！');
        }
    };

    const constructSearchQuery = () => '';

    const onPageChange = (page) => {
        setPage(page);
    };

    const changePageSize = (current, pageSize) => {
        setPage(1);
        setPageSize(pageSize);
    };

    const pagination = {
        total: total,
        pageSize: pageSize,
        current: page,
        showTotal: (total, range) => `总共${total}条记录`,
        onChange: onPageChange,
        showQuickJumper: true,
        showSizeChanger: true,
        onShowSizeChange: (current, pageSize) => changePageSize(current, pageSize),
    };

    const handleRowClick = (record) => {
        setVisible(true);
        setRecordTime(record.resultTime114)
        let idCounter = 1;
        var userResults = record.userResult && record.userResult.split("##") || [];
        var sysResults = record.sysResult && record.sysResult.split("##") || [];
        var wavFileArray = record.wavFileName && record.wavFileName.split("##") || [];
        var syswavFileArray = record.syswavFileName && record.syswavFileName.split("##") || [];
        var resultArray = [];
        for (var i = 0; i < Math.max(userResults.length, sysResults.length, wavFileArray.length, syswavFileArray.length); i++) {
            var userResult = userResults[i] ? userResults[i].trim() : "";
            var sysResult = sysResults[i] ? sysResults[i].trim() : "";
            var wavFileName = wavFileArray[i] ? wavFileArray[i].trim() : "";
            var syswavFileName = syswavFileArray[i] ? syswavFileArray[i].trim() : "";
            if (userResult !== "") {
                resultArray.push({ id: idCounter++, userResult: userResult, userWavName: wavFileName });
            }
            if (sysResult !== "") {
                resultArray.push({ id: idCounter++, sysResult: sysResult, sysWavName: syswavFileName });
            }
        }
        setSelectedRow(resultArray);
        setVisible(true);
    };

    const closeModal = () => {
        setVisible(false);
        setSelectedRow([]);
    };

    const handleStartDateChange = (_date, dateString) => {
        if (dateString) {
            setSearchStartDate(`${dateString} 00:00:00`);
        } else {
            setSearchStartDate(null);
        }
    };

    const handleEndDateChange = (_date, dateString) => {
        if (dateString) {
            setSearchEndDate(`${dateString} 23:59:59`);
        } else {
            setSearchEndDate(null);
        }
    };

    const handleSearch = () => {
        if ((searchStartDate && !searchEndDate) || (!searchStartDate && searchEndDate)) {
            message.error('请同时选择开始时间和结束时间');
            return;
        }
        if (searchStartDate && searchEndDate) {
            const startDate = new Date(searchStartDate);
            const endDate = new Date(searchEndDate);
            if (startDate > endDate) {
                message.error('结束时间必须大于开始时间');
                return;
            }
        }
        fetchLogs();
    };

    const handleChannelNumber = (ChannelNumber) => {
        setChannelNumber(ChannelNumber);
    };

    const columns = [
        {
            title: '序号',
            dataIndex: 'id',
            key: 'id',
            width: 80,
            align: 'center',
            render: (text, record, index) => (page - 1) * pageSize + index + 1
        },
        {
            title: '来电信息',
            key: 'callerInfo',
            width: 80,
            render: (_, record) => (
                <div className="auto114-caller">
                    <div className="auto114-caller-row">
                        <PhoneOutlined className="auto114-caller-icon phone" />
                        <span className="auto114-caller-strong">{record.callerNumber}</span>
                    </div>
                    <div className="auto114-caller-row">
                        <UserOutlined className="auto114-caller-icon user" />
                        <span>{record.callPersonnel}</span>
                    </div>
                    <div className="auto114-caller-meta">
                        {[record.callJob, record.callUnit].filter(Boolean).join(' | ')}
                    </div>
                </div>
            ),
        },
        {
            title: '用户内容',
            dataIndex: 'userResult',
            key: 'userResult',
            width: 120,
            ellipsis: {
                showTitle: false,
            },
            render: (userResult) => (
                <Tooltip placement="topLeft" title={userResult}>
                    <div className="auto114-pill auto114-pill-user">
                        {userResult && userResult.length > 20 ? userResult.substring(0, 20) + '...' : userResult}
                    </div>
                </Tooltip>
            ),
        },
        {
            title: '系统内容',
            dataIndex: 'sysResult',
            key: 'sysResult',
            width: 120,
            ellipsis: {
                showTitle: false,
            },
            render: (sysResult) => (
                <Tooltip placement="topLeft" title={sysResult}>
                    <div className="auto114-pill auto114-pill-system">
                        {sysResult && sysResult.length > 20 ? sysResult.substring(0, 20) + '...' : sysResult}
                    </div>
                </Tooltip>
            ),
        },
        
        {
            title: '记录时间',
            dataIndex: 'resultTime114',
            key: 'resultTime114',
            width: 80,
            render: (text) => {
                if (!text) return '';
                return (
                    <div className="auto114-time">
                        <CalendarOutlined className="auto114-time-icon" />
                        <span>
                            {moment(parseInt(text) * 1000).format('YYYY-MM-DD HH:mm:ss')}
                        </span>
                    </div>
                );
            },
        },
        {
            title: '操作',
            key: 'action',
            width: 80,
            align: 'center',
            render: (_, record) => (
                <Button 
                    type="primary" 
                    icon={<EyeOutlined />}
                    onClick={() => handleRowClick(record)}
                    size="small"
                >
                    查看详情
                </Button>
            ),
        },
    ];

    return (
        <div className="app-page">
            <div className="app-panel auto114-panel" style={{ marginBottom: '16px' }}>
                {/* 简洁的统计信息 */}
                <div className="auto114-stats">
                    <div className="auto114-stat-item">
                        <span className="auto114-stat-label">总记录</span>
                        <span className="auto114-stat-value accent">{total}</span>
                    </div>
                    <div className="auto114-stat-item">
                        <span className="auto114-stat-label">当前页</span>
                        <span className="auto114-stat-value green">{page}</span>
                    </div>
                    <div className="auto114-stat-item">
                        <span className="auto114-stat-label">每页</span>
                        <span className="auto114-stat-value orange">{pageSize}</span>
                    </div>
                    <div className="auto114-stat-item">
                        <span className="auto114-stat-label">已选</span>
                        <span className="auto114-stat-value purple">{selectedRowKeys.length}</span>
                    </div>
                </div>
            </div>

            {/* 搜索区域 */}
            <Card className="app-panel auto114-panel" style={{ marginBottom: '16px' }}>
                <Row gutter={[16, 16]} align="middle">
                    <Col span={8}>
                        <Space direction="vertical" style={{ width: '100%' }}>
                                <label className="auto114-filter-label">开始时间</label>
                                <DatePicker 
                                    showTime={false} 
                                    format="YYYY-MM-DD" 
                                    onChange={handleStartDateChange} 
                                    placeholder="选择开始时间"
                                    style={{ width: '100%' }}
                                />
                            </Space>
                        </Col>
                        <Col span={8}>
                            <Space direction="vertical" style={{ width: '100%' }}>
                                <label className="auto114-filter-label">结束时间</label>
                                <DatePicker 
                                    showTime={false} 
                                    format="YYYY-MM-DD" 
                                    onChange={handleEndDateChange} 
                                    placeholder="选择结束时间"
                                    style={{ width: '100%' }}
                                />
                            </Space>
                        </Col>
                        <Col span={8}>
                            <Space direction="vertical" style={{ width: '100%' }}>
                                <label className="auto114-filter-label">操作</label>
                                <Button 
                                    type="primary" 
                                    icon={<SearchOutlined />}
                                    onClick={handleSearch}
                                    style={{ width: '100%' }}
                                >
                                    查询记录
                                </Button>
                            </Space>
                        </Col>
                    </Row>
            </Card>

            {/* 数据表格区域 */}
            <Card className="app-panel auto114-panel">
                    <Table 
                        dataSource={dataSource} 
                        columns={columns}
                        className="auto114-table"
                        onRow={(record) => ({
                            onClick: () => handleRowClick(record),
                            style: { 
                                cursor: 'pointer'
                            }
                        })}
                        pagination={{
                            ...pagination,
                            showTotal: (total, range) => (
                                <span className="auto114-pagination">
                                    显示 {range[0]}-{range[1]} 条，共 {total} 条记录
                                </span>
                            )
                        }}
                        rowKey={record => record.id}
                        rowSelection={{
                            type: 'checkbox',
                            selectedRowKeys: selectedRowKeys,
                            onChange: setSelectedRowKeys,
                            getCheckboxProps: (record) => ({
                                name: record.id,
                            }),
                        }}
                        scroll={{ y: 600 }}
                        size="middle"
                    />
            </Card>

            <Modal
                title={
                    <div className="auto114-modal-title">
                        <AudioOutlined className="auto114-modal-icon" />
                        语音对话详情
                        <Tag 
                            color="blue" 
                            className="auto114-modal-tag"
                        >
                            {recordTime ? moment(parseInt(recordTime) * 1000).format('YYYY-MM-DD HH:mm:ss') : ''}
                        </Tag>
                    </div>
                }
                open={visible}
                onCancel={closeModal}
                className="auto114-modal"
                footer={null}
                width={1000}
                bodyStyle={{
                    maxHeight: '70vh',
                    overflow: 'auto',
                    padding: '20px'
                }}
                style={{ top: 20 }}
                centered
            >
                <div className="auto114-chat">
                    {selectedRow.map((item) => (
                        <div className={`auto114-chat-item ${item.userResult ? 'auto114-chat-user' : 'auto114-chat-system'}`} key={item.id}>
                            <div className="auto114-chat-text">
                                {item.userResult ? '用户：' : '系统：'} {item.userResult || item.sysResult}
                            </div>
                            {item?.userWavName && (
                                <div className="auto114-chat-audio">
                                    <audio src={`http://${config.serverIP}:${global.serverPORT}/record/${item.userWavName}`} controls controlsList="nodownload" />
                                </div>
                            )}
                            {item?.sysWavName && (
                                <div className="auto114-chat-audio">
                                    <audio src={`http://${config.serverIP}:${global.serverPORT}/tts/${item.sysWavName}`} controls controlsList="nodownload" />
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            </Modal>
        </div>
    );
};

export default Auto114Result;
