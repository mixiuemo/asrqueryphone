import React, { useState, useEffect } from 'react';
import { Table, Button, Space, Modal, Form, Input, message, Upload, Radio } from 'antd';
import { ExclamationCircleOutlined, UploadOutlined, PlayCircleOutlined } from '@ant-design/icons';
import { debounce } from 'lodash';
import { getEmbedding, createEmbedding, updateEmbedding, deleteEmbedding } from '../services/api';
import {
  getAllTrainConfigs,
  getTrainConfigById,
  getTrainConfig,
  createTrainConfig,
  updateTrainConfig,
  deleteTrainConfig
} from '../services/api'; // 假设这是你保存 trainConfig 前端调用方法的文件路径
const { confirm } = Modal;
const API_BASE_URL = 'http://localhost:5000/api';

const TrainConfig = () => {
  const [data, setData] = useState([]);
  const [processedDataSource, setProcessedDataSource] = useState([]);
  const [loading, setLoading] = useState(false);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [editingService, setEditingService] = useState(null);
  const [form] = Form.useForm();
  const [fileName, setFileName] = useState('');
  const [uploadName, setUploadName] = useState('');
  const [originName, setOriginName] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [audioUrl, setAudioUrl] = useState(null);
  const [isFileUploaded, setIsFileUploaded] = useState(false);
  const [embedding, setEmbedding] = useState('');
  const [selectedOption, setSelectedOption] = useState('upload'); // 'upload' 或 'record'
  const [isRecording, setIsRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState(null);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [audioChunks, setAudioChunks] = useState([]);
  const [playName, setPlayName] = useState('');

  // 新增测试声纹相关状态
  const [testVoiceVisible, setTestVoiceVisible] = useState(false);
  const [testVoiceTitle, setTestVoiceTitle] = useState('');
  const [whoIs, setWhoIs] = useState('');


  useEffect(() => {
    fetchData();
    const intervalId = setInterval(() => {
      fetchData();
    }, 30000);
    return () => clearInterval(intervalId);
  }, []);

  const fetchData = async (searchQuery = '') => {
    setLoading(true);
    try {
      const result = await getTrainConfig(searchQuery);
      setData(result);
      // 生成从 1 开始的序号
      setProcessedDataSource(result.map((item, index) => ({
        ...item,
        displayId: index + 1, // 为每条记录添加一个 displayId 字段，从 1 开始
      })))
    } catch (error) {
      message.error('获取数据失败');
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

  const handlePlayAudio = (fileUrl) => {
    setAudioUrl(fileUrl);
    const audio = new Audio(fileUrl);
    audio.play().catch(e => console.error('Error playing audio:', e));
  };

  const handleFileUpload = (info) => {
    const { status, response } = info.file;

    if (status === 'uploading') {
      return;
    }
    if (status === 'done') {
      if (response && response.status === 'success') {
        setPlayName(response?.file_path.replace(/[/\\]/g, '/').split('/').pop())
        message.success(`录音文件上传成功，共上传 1 个文件`);
        setUploadName(response?.file_path.replace(/[/\\]/g, '/').split('/').pop())
        setFileName(response?.file_path);
        setIsFileUploaded(true);
        form.setFieldsValue({
          fileName: response?.file_path,
          file: response.fileUrl
        });
        fetchData();
      } else {
        message.error('文件上传失败，服务器返回错误');
      }
    } else if (status === 'error') {
      message.error('文件上传失败，请重试');
    }
  };

  const handleCreate = () => {
    form.resetFields();
    setPlayName('');
    setEditingService(null);
    setIsModalVisible(true);
    setFileName('');
    setAudioUrl(null);
    setIsFileUploaded(false);
    setSelectedOption('upload');
    setIsRecording(false);
    setAudioBlob(null);
    setAudioChunks([]);
  };

  // 新增handleCancel方法
  const handleCancel = () => {
    setTestVoiceVisible(false);
    // 可以在这里添加其他清理逻辑
    setWhoIs('');
  };

  const handleEdit = (record) => {
    setPlayName(record?.ref_file.replace(/[/\\]/g, '/').split('/').pop())
    setOriginName(record.uploadName)
    form.setFieldsValue({
      ...record,
      fileName: record.ref_file || ''
    });
    setEditingService(record);
    setIsModalVisible(true);
    setFileName(record.ref_file || '');
    setAudioUrl(record.ref_file);
    setIsFileUploaded(true);
    setSelectedOption('upload');
  };

  const handleDelete = async (id) => {
    try {
      await deleteTrainConfig(id);
      message.success('记录删除成功');
      fetchData();
    } catch (error) {
      message.error('记录删除失败');
    }
  };

  const showDeleteConfirm = (id, service) => {
    confirm({
      title: '确定要删除这条记录吗？',
      icon: <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />,
      content: `即将删除记录 ${service} (ID: ${id})`,
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
      values.ref_file = values.fileName
      if (originName == uploadName) {
        setIsModalVisible(false)
      }
      values.embedding = JSON.stringify(embedding);
      values.uploadName = uploadName;
      if (editingService) {
        await updateTrainConfig(editingService.id, values);
        message.success('记录更新成功');
      } else {
        await createTrainConfig(values);
        message.success('记录创建成功');
      }
      setIsModalVisible(false);
      fetchData();
    } catch (error) {
      message.error('操作失败');
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const chunks = [];
      setAudioChunks(chunks);
      const recorder = new MediaRecorder(stream);
      setMediaRecorder(recorder);

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunks.push(event.data);
        }
      };

      recorder.onstop = async () => {
        const blob = new Blob(chunks, { type: 'audio/wav' });
        setAudioBlob(blob);
        stream.getTracks().forEach(track => track.stop());
        uploadRecordedAudio(blob);
      };

      recorder.start();
      setIsRecording(true);
    } catch (error) {
      console.error('录音失败:', error);
      message.error('录音失败，请确保麦克风已启用');
    }
  };

  const stopRecording = () => {
    if (mediaRecorder) {
      mediaRecorder.stop();
      setIsRecording(false);
    }
  };

  const uploadRecordedAudio = async (blob) => {
    const file = new File([blob], 'recorded-audio.wav', { type: 'audio/wav' });
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API_BASE_URL}/upload/upload`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`
        },
        body: formData
      });

      const data = await response.json();
      if (data.status === 'success') {
        message.success(`录音文件上传成功，共上传 1 个文件`);
        const uploadedFileName = data.fileName || 'recorded-audio.wav';
        setFileName(data?.file_path);
        setIsFileUploaded(true);
        form.setFieldsValue({
          fileName: data?.file_path,
          file: data.fileUrl
        });
        setPlayName(data?.file_path.replace(/[/\\]/g, '/').split('/').pop())
        // 替换文件路径中的正斜杠为反斜杠
        setUploadName(data?.file_path.replace(/[/\\]/g, '/').split('/').pop())
        fetchData();
      } else {
        message.error('录音文件上传失败，服务器返回错误');
      }
    } catch (error) {
      message.error('录音文件上传失败，请重试');
    }
  };

  const columns = [
    {
      title: 'ID',
      dataIndex: 'displayId',
      key: 'displayId',
    },
    {
      title: '文件内容',
      dataIndex: 'ref_text',
      key: 'ref_file',
    },
    {
      title: '文件路径',
      dataIndex: 'ref_file',
      key: 'ref_file',
      render: (text, record) => (
        <Space>
          {text}
          {record.fileUrl && (
            <Button
              type="text"
              icon={<PlayCircleOutlined />}
              onClick={() => handlePlayAudio(record.fileUrl)}
            />
          )}
        </Space>
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space size="middle">
          <Button onClick={() => handleEdit(record)}>编辑</Button>
          <Button
            danger
            onClick={() => showDeleteConfirm(record.id, record.speakerName)}
          >
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
          placeholder="搜索服务或ID"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onPressEnter={handleSearch}
          style={{ width: 300 }}
        />
        <Button type="primary" onClick={handleSearch}>
          搜索
        </Button>
        <Upload
          name="file"
          action={`${API_BASE_URL}/upload/upload`}
          headers={{
            Authorization: `Bearer ${localStorage.getItem('token')}`
          }}
          onChange={handleFileUpload}
          showUploadList={false}
        >
          {/* <Button type="primary" style={{ marginLeft: 16 }}>
                        上传文件
                    </Button> */}
        </Upload>
        <Button type="primary" onClick={handleCreate} style={{ marginLeft: 16 }}>
          添加训练配置
        </Button>
      </Space>

      <Table
        columns={columns}
        dataSource={processedDataSource}
        rowKey="id"
        loading={loading}
        scroll={{ x: 1500, y: 640 }}
      />

      <Modal
        title={editingService ? '编辑训练配置' : '添加训练配置'}
        open={isModalVisible}
        onOk={handleSubmit}
        onCancel={() => setIsModalVisible(false)}
        width={600}
      >
        <Form form={form} layout="vertical" initialValues={{ option: 'upload' }}>
          <Form.Item
            name="ref_text"
            label="文件内容"
            rules={[{ required: true, message: '请输入文件内容!' }]}
          >
            <Input />
          </Form.Item>

          <Form.Item name="option" label="选择上传方式（：上传文件和录音选一个即可）">
            <Radio.Group onChange={(e) => {
              setSelectedOption(e.target.value)
            }} value={selectedOption}>
              <Radio value="upload">上传文件</Radio>
              <Radio value="record">录音</Radio>
            </Radio.Group>
          </Form.Item>
          <div>
            <Form.Item
              name="fileName"
              label="文件路径"
            // rules={[{ required: true, message: '请输入用户名!' }]}
            >
              <Input readOnly placeholder="上传或者录音后自动填充" />
            </Form.Item>
            {playName ? <audio
              src={'http://localhost:5000/media/' + playName}
              controls
            /> : <></>}
          </div>



          {selectedOption === 'upload' ? (
            !isFileUploaded ? (
              <Form.Item
                name="file"
                label="上传文件"
                rules={[{ required: true, message: '请选择文件!' }]}
              >
                <Upload
                  name="file"
                  action={`${API_BASE_URL}/upload/upload`}
                  headers={{
                    Authorization: `Bearer ${localStorage.getItem('token')}`
                  }}
                  onChange={handleFileUpload}
                  showUploadList={false}
                >
                  <Button icon={<UploadOutlined />}>选择文件</Button>
                </Upload>
              </Form.Item>
            ) : (
              <Form.Item
                label="已上传文件"
              >
                <div style={{ display: 'flex', alignItems: 'center' }}>
                  <span style={{ marginRight: 8 }}>{fileName}</span>
                  {/* <Button
                    type="text"
                    onClick={() => handlePlayAudio(form.getFieldValue('file'))}
                  /> */}
                  <Button
                    type="link"
                    onClick={() => {
                      setIsFileUploaded(false);
                      setFileName('');
                      setPlayName('');
                      form.setFieldsValue({
                        fileName: '',
                        file: null
                      });
                    }}
                  >
                    重新上传
                  </Button>
                </div>
              </Form.Item>
            )
          ) : (
            <div>
              <Form.Item label="录音">
                <Space style={{ marginBottom: 16 }}>
                  <Button onClick={startRecording} disabled={isRecording}>
                    开始录音
                  </Button>
                  <Button onClick={stopRecording} disabled={!isRecording}>
                    结束录音
                  </Button>
                </Space>
                {/* {audioBlob && (
                                    <audio
                                        src={URL.createObjectURL(audioBlob)}
                                        controls
                                    />
                                )} */}
                {!audioBlob && (
                  <div style={{ textAlign: 'center', padding: '20px', border: '1px dashed #ccc', borderRadius: '4px' }}>
                    <p>请开始录音</p>
                  </div>
                )}
              </Form.Item>
            </div>
          )}

          <Form.Item
            name="fileName"
            hidden
          >
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default TrainConfig;