import React, { useState, useEffect, useMemo } from 'react';
import { Button, Space, message, Row, Col, Input, Statistic, Tooltip, Empty } from 'antd';
import { SearchOutlined, CopyOutlined } from '@ant-design/icons';

import {
    writeHotwords,
    readHotwords
} from '../services/api';

const Ai114Keywords = () => {
    const [data, setData] = useState([]);
    const [loading, setLoading] = useState(false);
    const [searchText, setSearchText] = useState('');
    const [debouncedSearch, setDebouncedSearch] = useState('');
    const [filteredData, setFilteredData] = useState([]);

    const MAX_RENDER_ITEMS = 500;

    useEffect(() => {
        loadHotwords();
    }, []);

    // 搜索功能
    useEffect(() => {
        const timer = setTimeout(() => {
            setDebouncedSearch(searchText.trim());
        }, 300);
        return () => clearTimeout(timer);
    }, [searchText]);

    useEffect(() => {
        if (debouncedSearch) {
            const filtered = data.filter(item =>
                item.hotword.toLowerCase().includes(debouncedSearch.toLowerCase())
            );
            setFilteredData(filtered);
        } else {
            setFilteredData(data);
        }
    }, [debouncedSearch, data]);

    const visibleData = useMemo(
        () => filteredData.slice(0, MAX_RENDER_ITEMS),
        [filteredData]
    );

    const loadHotwords = async () => {
        setLoading(true);
        try {
            const result = await readHotwords();
            if (result.status === 200) {
                // 将字符串数组转换为对象数组
                const hotwordsArray = result.details.hotwords || [];
                const formattedData = hotwordsArray.map((hotword, index) => ({
                    key: index,
                    hotword: hotword
                }));
                setData(formattedData);
                setFilteredData(formattedData);
            }
        } catch (error) {
            message.error('读取热词失败');
            console.error('Error loading hotwords:', error);
        } finally {
            setLoading(false);
        }
    };



    const handleWriteHotwords = async () => {
        setLoading(true);
        try {
            const result = await writeHotwords();
            if (result.status === 200) {
                message.success(`热词写入成功！生成了${result.details.total_hotwords}个热词`);
                // 写入成功后重新读取热词列表
                await loadHotwords();
            } else {
                message.error('热词写入失败');
            }
        } catch (error) {
            message.error('热词写入失败：' + error.message);
        } finally {
            setLoading(false);
        }
    };


    const handleCopy = (text) => {
        navigator.clipboard.writeText(text).then(() => {
            message.success(`已复制热词: ${text}`);
        }).catch(() => {
            message.error('复制失败');
        });
    };

    return (
        <div className="app-page hotword-page">
            <Row gutter={16} style={{ marginBottom: '16px' }}>
                <Col span={24}>
                    <div className="app-panel hotword-summary">
                        <Statistic
                            title="热词总数"
                            value={data.length}
                            valueStyle={{ color: '#00d4ff', fontSize: '28px' }}
                        />
                        <div className="hotword-summary-meta">
                        {searchText
                            ? `搜索到 ${filteredData.length} 个热词`
                            : `共 ${data.length} 个热词`}
                        {filteredData.length > MAX_RENDER_ITEMS && (
                            <span className="hotword-summary-note">
                                仅展示前 {MAX_RENDER_ITEMS} 条
                            </span>
                        )}
                        </div>
                    </div>
                </Col>
            </Row>

            <div className="app-panel hotword-actions">
                <div className="hotword-actions-left">
                    <div className="hotword-title">热词配置</div>
                    <div className="hotword-subtitle">热词用于提升特定领域词识别准确率，写入后可让系统优先召回这些关键词</div>
                </div>
                <div className="hotword-actions-right">
                    <Input.Search
                        placeholder="搜索热词..."
                        value={searchText}
                        onChange={(e) => setSearchText(e.target.value)}
                        onSearch={setSearchText}
                        allowClear
                        enterButton={<SearchOutlined />}
                        className="hotword-search"
                    />
                    <Button type="primary" onClick={handleWriteHotwords} className="hotword-write-btn">
                        写入热词
                    </Button>
                </div>
            </div>

            <div className="app-panel hotword-list-panel">
                {loading ? (
                    <div className="hotword-loading">正在加载热词...</div>
                ) : filteredData.length === 0 ? (
                    <Empty description="暂无热词" />
                ) : (
                    <div className="hotword-grid">
                        {visibleData.map((item) => (
                            <div
                                key={item.key}
                                className="hotword-chip"
                                onClick={() => handleCopy(item.hotword)}
                            >
                                <span className="hotword-chip-text">{item.hotword}</span>
                                <Tooltip title="复制">
                                    <CopyOutlined className="hotword-chip-icon" />
                                </Tooltip>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export default Ai114Keywords;
