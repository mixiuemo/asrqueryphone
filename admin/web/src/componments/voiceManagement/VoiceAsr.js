import React, { useState, useEffect, useRef } from 'react';
import { 
  Table, Button, Modal, Input, Slider, message, Form, Radio, Tag, Row, Col,  
  Checkbox, Collapse, Tooltip, Progress, Popconfirm, Upload, Space
} from 'antd';
import { 
  FolderOpenOutlined, EditOutlined, SaveOutlined, CloseOutlined, 
  PlayCircleOutlined, PauseOutlined, DeleteOutlined, PlusOutlined,
  SoundOutlined, StepForwardOutlined, StepBackwardOutlined, UploadOutlined
} from '@ant-design/icons';


import WaveSurfer from 'wavesurfer.js';
import Regions from 'wavesurfer.js/dist/plugins/regions.js';

import { getAudioFiles, clipAudioFile, createEmbedding } from '../../services/api';
// import VoiceForm from './VoiceForm'; // 复用声纹列表中的表单组件

const { Panel } = Collapse;
// const API_BASE_URL = 'http://'+window.location.hostname+':8114/process_audio';
const API_BASE_URL = 'http://192.168.40.246:8114/process_audio';

const VoiceAsr = ({ switchToVoiceList }) => {
    const [directory, setDirectory] = useState('');
    const [audioFiles, setAudioFiles] = useState([]);
    const [loading, setLoading] = useState(false);
    const [editingFile, setEditingFile] = useState(null);
    const [waveform, setWaveform] = useState(null);
    const [isWaveVisible, setIsWaveVisible] = useState(false);
    const [clipStart, setClipStart] = useState(0);
    const [clipEnd, setClipEnd] = useState(0);
    const [duration, setDuration] = useState(0);
    const [selectedRegion, setSelectedRegion] = useState(null);
    const [isFormVisible, setIsFormVisible] = useState(false);
    const [clippedFile, setClippedFile] = useState(null);
    const [form] = Form.useForm();

    
    // 波形相关状态
    const waveformRef = useRef(null);
    const regionsRef = useRef(null);
    const [isPlaying, setIsPlaying] = useState(false);
    const [isPlayingRegion, setIsPlayingRegion] = useState(false);
    const [currentRegionIndex, setCurrentRegionIndex] = useState(0);
    const [playbackProgress, setPlaybackProgress] = useState(0);


    // 剪辑区域状态
    const [regions, setRegions] = useState([]);
    const [selectedRegions, setSelectedRegions] = useState([]);
    const [compositeAudio, setCompositeAudio] = useState(null);
    const [isPlayingComposite, setIsPlayingComposite] = useState(false);
    const [compositeProgress, setCompositeProgress] = useState(0);


    const [uploadName, setUploadName] = useState('');
    const [fileName, setFileName] = useState('');
    const [isFileUploaded, setIsFileUploaded] = useState(false);
    const [embedding, setEmbedding] = useState('');
    const [selectedOption, setSelectedOption] = useState('upload'); // 'upload' 或 'record'
    const [userType, setUserType] = useState('1'); // '1' 或 '2' 或 '3'
    const [isRecording, setIsRecording] = useState(false);
    const [audioBlob, setAudioBlob] = useState(null);
    const [mediaRecorder, setMediaRecorder] = useState(null);
    const [audioChunks, setAudioChunks] = useState([]);
    const [playName, setPlayName] = useState('');

    // 新增测试声纹相关状态
    const [testVoiceVisible, setTestVoiceVisible] = useState(false);
    const [testVoiceTitle, setTestVoiceTitle] = useState('');
    const [whoIs, setWhoIs] = useState('');

    const [selectedRowKeys, setSelectedRowKeys] = useState([]); // 选中的行的键值
    const [selectedRows, setSelectedRows] = useState([]); // 选中的行数据

  // 修复1: 使用 ref 存储当前区域数据
  const currentRegionRef = useRef(null);
  const timeUpdateHandlerRef = useRef(null);


    useEffect(() => {
        return () => {
        if (waveformRef.current) {
            waveformRef.current.destroy();
        }
        if (compositeAudio && compositeAudio.pause) {
            compositeAudio.pause();
        }
        // if (timeUpdateHandlerRef.current && waveformRef.current) {
        //     waveformRef.current.un('timeupdate', timeUpdateHandlerRef.current);
        // }
        };
    }, []);

  const fetchData = () => {
    loadDirectory();
    
  }
  const loadDirectory = async () => {
    if (!directory) {
      message.warning('请输入文件夹路径');
      return;
    }
    setLoading(true);
    try {
      const files = await getAudioFiles(directory);
      setAudioFiles(files.map((file, index) => ({
        ...file,
        key: index,
        displayId: index + 1,
      })));
    } catch (error) {
      message.error('加载音频文件失败');
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (file) => {
    setEditingFile(file);
    setIsWaveVisible(true);
    setRegions([]);
    setSelectedRegions([]);
    setCompositeAudio(null);
    setCompositeProgress(0);
    setCurrentRegionIndex(0);
    
    // 延迟加载确保 DOM 已渲染
    setTimeout(() => {
      initWaveform(file.filePath);
    }, 100);
  };


  const initWaveform = (filePath) => {
    // 清除之前的波形
    if (waveformRef.current) {
      waveformRef.current.destroy();
      setIsPlaying(false);
      setIsPlayingRegion(false);
    }

    // 创建 WaveSurfer 实例
    const wavesurfer = WaveSurfer.create({
      container: '#waveform',
      waveColor: '#4F46E5',
      progressColor: '#2563EB',
      cursorColor: '#1E40AF',
      height: 150,
      barWidth: 2,
      barGap: 1,
      autoCenter: true
    });

    // 注册区域插件
    regionsRef.current = wavesurfer.registerPlugin(
      Regions.create({
        regions: [],
        dragSelection: {
          slop: 5
        }
      })
    );

    // 加载音频文件
    wavesurfer.load(`${API_BASE_URL}/`);
    
    wavesurfer.on('ready', (start, end) => {
      console.log("start:",start,"end:",  end)
      const dur = wavesurfer.getDuration();
      setDuration(dur);
      
      // 添加初始区域
      const region = regionsRef.current.addRegion({
        id: 'region-1',
        start: 0,
        end: dur,
        content: '区域1',
        color: 'rgba(79, 70, 229, 0.3)',
        drag: true,
        resize: true
      });
      
      // 监听区域更新事件
      region.on('update-end', () => {
        updateRegion(region.id, region.start, region.end);
      });
      
    //   // 监听播放进度
      wavesurfer.on('timeupdate', (time) => {
        setPlaybackProgress((time / dur) * 100);
      });
    //   wavesurfer.on('timeupdate', timeUpdateHandlerRef.current);
    
      // 修复：监听暂停事件
      wavesurfer.on('pause', () => {
        setIsPlaying(false);
        setIsPlayingRegion(false);
      });

      // 监听播放结束事件
      wavesurfer.on('finish', () => {
        setIsPlaying(false);
        setIsPlayingRegion(false);
        setPlaybackProgress(0);
      });

      
      // 保存区域到状态
      setRegions([{
        id: region.id,
        start: region.start,
        end: region.end,
        content: '区域1',
        color: 'rgba(79, 70, 229, 0.3)'
      }]);
    });

    waveformRef.current = wavesurfer;
  };

// 添加新区域
  const addRegion = () => {
    if (!waveformRef.current || regions.length >= 5) {
      message.warning('最多只能添加5个区域');
      return;
    }
    
    const duration = waveformRef.current.getDuration();
    const newRegionId = `region-${Date.now()}`;
    const newRegion = regionsRef.current.addRegion({
      id: newRegionId,
      start: duration * 0.2 * regions.length,
      end: duration * (0.2 * regions.length + 0.2),
      content: `区域${regions.length + 1}`,
      color: getRandomColor(),
      drag: true,
      resize: true
    });

    // 修复4: 为新区域绑定更新事件
    newRegion.on('update-end', () => {
      updateRegion(newRegion.id, newRegion.start, newRegion.end);
    });
    
    setRegions(prev => [
      ...prev, 
      {
        id: newRegionId,
        start: newRegion.start,
        end: newRegion.end,
        content: `区域${regions.length + 1}`,
        color: newRegion.color
      }
    ]);
  };

  // 更新区域
  const updateRegion = (id, start, end) => {
    setRegions(prev => 
      prev.map(region => 
        region.id === id ? { ...region, start, end } : region
      )
    );
  };

  // 删除区域
  const deleteRegion = (id) => {
    const region = regionsRef.current.getRegions().find(r => r.id === id);
    if (region) {
      region.remove();
    }
    
    setRegions(prev => prev.filter(r => r.id !== id));
    setSelectedRegions(prev => prev.filter(rId => rId !== id));
  };

  // 播放整个音频
  const playFullAudio = () => {
    if (waveformRef.current) {
      waveformRef.current.play();
      setIsPlaying(true);
      setIsPlayingRegion(false);
      currentRegionRef.current = null;
    }
  };

  // 播放选中区域
  const playSelectedRegion = () => {
    debugger;
    if (waveformRef.current && selectedRegions.length > 0) {
      const regionId = selectedRegions[currentRegionIndex];
      const region = regionsRef.current.getRegions().find(r => r.id === regionId);
      if (region) {
        // 修复：只播放选中的区域，而不是整个音频
        waveformRef.current.setTime(region.start);
        waveformRef.current.play(region.start, region.end);
        setIsPlayingRegion(true);
        setIsPlaying(false);
        // 监听播放进度（只针对这个区域）
        waveformRef.current.on('timeupdate', (currentTime) => {
            const regionDuration = region.end - region.start;
            // const progress = ((currentTime - region.start) / regionDuration) * 100;
            //   setPlaybackProgress(progress);
          const progress = (currentTime / region.end) * 100
          console.log("当前播放进度:", progress)
          setPlaybackProgress(progress);
          if (currentTime >= region.end) {
            waveformRef.current.stop()
          }
        });
      }
    }
  };
      // 播放选中区域
//   const playSelectedRegion = () => {
//     if (waveformRef.current && selectedRegions.length > 0) {
//       const regionId = selectedRegions[currentRegionIndex];
//       const region = regionsRef.current.getRegions().find(r => r.id === regionId);
      
//       if (region) {
//         // 修复5: 存储当前区域引用
//         currentRegionRef.current = {
//           id: region.id,
//           start: region.start,
//           end: region.end
//         };
        
//         // 设置播放起始位置
//         waveformRef.current.setTime(region.start);
        
//         // 只播放选中的区域
//         waveformRef.current.play(region.start, region.end);
        
//         setIsPlayingRegion(true);
//         setIsPlaying(false);
//       }
//     }
//   };


//   // 播放上一个区域
  const playPrevRegion = () => {
    if (selectedRegions.length === 0) return;
    
    const newIndex = (currentRegionIndex - 1 + selectedRegions.length) % selectedRegions.length;
    setCurrentRegionIndex(newIndex);
    
    const regionId = selectedRegions[newIndex];
    const region = regionsRef.current.getRegions().find(r => r.id === regionId);
    
    if (region) {
      waveformRef.current.setTime(region.start);
      waveformRef.current.play(region.start, region.end);
      setIsPlayingRegion(true);
      setIsPlaying(false);
    }
  };

  // 播放上一个区域
//   const playPrevRegion = () => {
//     if (selectedRegions.length === 0) return;
    
//     const newIndex = (currentRegionIndex - 1 + selectedRegions.length) % selectedRegions.length;
//     setCurrentRegionIndex(newIndex);
//     playSelectedRegion();
//   };

  // 播放下一个区域
  const playNextRegion = () => {
    if (selectedRegions.length === 0) return;
    
    const newIndex = (currentRegionIndex + 1) % selectedRegions.length;
    setCurrentRegionIndex(newIndex);
    
    const regionId = selectedRegions[newIndex];
    const region = regionsRef.current.getRegions().find(r => r.id === regionId);
    
    if (region) {
      waveformRef.current.setTime(region.start);
      waveformRef.current.play(region.start, region.end);
      setIsPlayingRegion(true);
      setIsPlaying(false);
    }
  };
    // 播放下一个区域
//   const playNextRegion = () => {
//     if (selectedRegions.length === 0) return;
    
//     const newIndex = (currentRegionIndex + 1) % selectedRegions.length;
//     setCurrentRegionIndex(newIndex);
//     playSelectedRegion();
//   };

  // 暂停播放
  const pauseAudio = () => {
    if (waveformRef.current) {
      waveformRef.current.pause();
      setIsPlaying(false);
      setIsPlayingRegion(false);
    }
    
    if (compositeAudio && compositeAudio.pause) {
      compositeAudio.pause();
      setIsPlayingComposite(false);
    }
  };

  // 组合截取
  const handleCompositeClip = async () => {
    // if (selectedRegions.length === 0) {
    //   message.warning('请至少选择一个区域');
    //   return;
    // }

    // try {
    //   setLoading(true);
      
    //   // 获取选中的区域数据
    //   const regionsToClip = regions.filter(r => selectedRegions.includes(r.id));
      
    //   const result = await clipAudioFile({
    //     filePath: editingFile.filePath,
    //     regions: regionsToClip.map(region => ({
    //       start: region.start,
    //       end: region.end
    //     }))
    //   });

    //   setClippedFile({
    //     ...result,
    //     fileName: `composite_${editingFile.fileName}`
    //   });
      
    //   message.success('音频组合剪辑成功');
      
    //   // 创建组合音频用于预览
    //   const audio = new Audio(`${API_BASE_URL}/embedding/file?path=${encodeURIComponent(result.filePath)}`);
    //   setCompositeAudio(audio);
      
    //   // 监听组合音频进度
    //   audio.addEventListener('timeupdate', () => {
    //     setCompositeProgress((audio.currentTime / audio.duration) * 100);
    //   });
      
    //   audio.addEventListener('ended', () => {
    //     setIsPlayingComposite(false);
    //     setCompositeProgress(0);
    //   });
    // } catch (error) {
    //   message.error('音频剪辑失败');
    // } finally {
    //   setLoading(false);
    // }
    if (selectedRegions.length === 0) {
        message.warning('请至少选择一个区域');
        return;
    }

    try {
        setLoading(true);
        // 获取选中的区域数据
        const regionsToClip = regions.filter(r => selectedRegions.includes(r.id));
        
        const result = await clipAudioFile({
            filePath: editingFile.filePath,
            regions: regionsToClip.map(region => ({
                start: region.start,
                end: region.end
            }))
        });

        // 替换文件路径中的正斜杠为反斜杠
        const windowsFilePath = result.filePath;
        debugger
        // 调用后端接口
        fetch('http://'+window.location.hostname+':5004/identify', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                file_path: windowsFilePath  // 使用后端返回的文件路径
            })
        })
        .then(response => response.json())
        .then(data => {
            setEmbedding(data.embedding)
            console.log('接口返回数据:', data);
            // 处理接口返回的数据，例如显示用户名和处理时间
            // message.info(`识别结果：${data.username}，处理时间：${data.time}秒`);
        })
        .catch(error => {
            console.error('接口调用失败:', error);
            // message.error('识别失败，请重试');
        });

        setClippedFile({
        ...result,
        fileName: `composite_${editingFile.fileName}`
        });
        
        message.success('音频组合剪辑成功');
        
        // 修复：创建音频 URL 而不是 Audio 对象
        const audioUrl = `${API_BASE_URL}/embedding/file?path=${encodeURIComponent(result.filePath)}`;
        setCompositeAudio(audioUrl);


        
        // 修复：打开注册模态框
        setIsWaveVisible(false);
        setIsFormVisible(true);
        
    } catch (error) {
        message.error('音频剪辑失败');
    } finally {
        setLoading(false);
    } 
  };

  // 播放组合音频
  const playCompositeAudio = () => {
    // if (compositeAudio) {
    //   compositeAudio.play();
    //   setIsPlayingComposite(true);
    // }
    if (compositeAudio) {
        // 创建新的 Audio 对象并播放
        const audio = new Audio(compositeAudio);
        audio.play();
        
        // 监听播放进度
        audio.addEventListener('timeupdate', () => {
        if (audio.duration > 0) {
            setCompositeProgress((audio.currentTime / audio.duration) * 100);
        }
        });
        
        // 监听播放结束
        audio.addEventListener('ended', () => {
        setIsPlayingComposite(false);
        setCompositeProgress(0);
        });
        
        setIsPlayingComposite(true);
    }
  };

  // 注册组合音频
  const handleRegisterComposite = async () => {
    if (!clippedFile) return;
    
    try {
      await createEmbedding({
        ...form.getFieldsValue(),
        file: clippedFile.filePath,
        fileName: clippedFile.fileName,
        embedding: JSON.stringify(embedding)
      });
      
      message.success('声纹注册成功');
      setIsFormVisible(false);
      form.resetFields();
      switchToVoiceList();
    } catch (error) {
      message.error('声纹注册失败');
    }
  };





  const handleClip = async () => {
    if (!selectedRegion || !editingFile) {
      message.warning('请先选择剪辑区域');
      return;
    }

    try {
      setLoading(true);
      const result = await clipAudioFile({
        filePath: editingFile.filePath,
        start: clipStart,
        end: clipEnd
      });

      setClippedFile({
        ...result,
        fileName: `clipped_${editingFile.fileName}`
      });
      
      message.success('音频剪辑成功');
      setIsWaveVisible(false);
      setIsFormVisible(true);
    } catch (error) {
      message.error('音频剪辑失败');
    } finally {
      setLoading(false);
    }
  };

   // 生成随机颜色
  const getRandomColor = () => {
    const colors = [
      'rgba(255, 99, 132, 0.3)',
      'rgba(54, 162, 235, 0.3)',
      'rgba(255, 206, 86, 0.3)',
      'rgba(75, 192, 192, 0.3)',
      'rgba(153, 102, 255, 0.3)'
    ];
    return colors[Math.floor(Math.random() * colors.length)];
  };


  // 处理表单提交
  const handleFormSubmit = async (values) => {
    if (!clippedFile) return;
    
    try {
      await createEmbedding({
        ...values,
        file: clippedFile.filePath,
        fileName: clippedFile.fileName,
        embedding: JSON.stringify(embedding)
      });
      
      message.success('声纹注册成功');
      setIsFormVisible(false);
      form.resetFields();
      switchToVoiceList();
    } catch (error) {
      message.error('声纹注册失败');
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

    const handleFileUpload = (info) => {
        const { status, response } = info.file;

        if (status === 'uploading') {
            return;
        }
        if (status === 'done') {
            if (response && response.status === 'success') {
                setPlayName(response?.file_path.replace(/[/\\]/g, '/').split('/').pop())
                message.success(`录音文件上传成功，共上传 1 个文件`);

                const uploadedFileName = response.fileName || info.file.name;
                setUploadName(response?.file_path.replace(/[/\\]/g, '/').split('/').pop())
                setFileName(uploadedFileName);
                setIsFileUploaded(true);
                form.setFieldsValue({
                    fileName: uploadedFileName,
                    file: response.fileUrl
                });

                // 替换文件路径中的正斜杠为反斜杠
                const windowsFilePath = response?.file_path?.replace(/\/+/g, '\\\\');
                // 调用后端接口
                fetch('http://'+window.location.hostname+':5004/identify', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        file_path: windowsFilePath  // 使用后端返回的文件路径
                    })
                })
                    .then(response => response.json())
                    .then(data => {
                        setEmbedding(data.embedding)
                        console.log('接口返回数据:', data);
                        // 处理接口返回的数据，例如显示用户名和处理时间
                        // message.info(`识别结果：${data.username}，处理时间：${data.time}秒`);
                    })
                    .catch(error => {
                        console.error('接口调用失败:', error);
                        // message.error('识别失败，请重试');
                    });

                fetchData();
            } else {
                message.error('文件上传失败，服务器返回错误');
            }
        } else if (status === 'error') {
            message.error('文件上传失败，请重试');
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
                setFileName(uploadedFileName);
                setIsFileUploaded(true);
                form.setFieldsValue({
                    fileName: uploadedFileName,
                    file: data.fileUrl
                });
                setPlayName(data?.file_path.replace(/[/\\]/g, '/').split('/').pop())
                // 替换文件路径中的正斜杠为反斜杠
                setUploadName(data?.file_path.replace(/[/\\]/g, '/').split('/').pop())
                const windowsFilePath = data?.file_path?.replace(/\/+/g, '\\\\');
                // 调用后端接口
                fetch('http://'+window.location.hostname+':5004/identify', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        file_path: windowsFilePath  // 使用后端返回的文件路径
                    })
                })
                    .then(response => response.json())
                    .then(data => {
                        setEmbedding(data.embedding)
                        console.log('接口返回数据:', data);
                        // 处理接口返回的数据，例如显示用户名和处理时间
                        // message.info(`识别结果：${data.username}，处理时间：${data.time}秒`);
                    })
                    .catch(error => {
                        console.error('接口调用失败:', error);
                        // message.error('识别失败，请重试');
                    });

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
      title: '序号',
      dataIndex: 'displayId',
      key: 'displayId',
      width: 80,
    },
    {
      title: '文件名',
      dataIndex: 'fileName',
      key: 'fileName',
      render: (text) => <Tag color="blue">{text}</Tag>,
    },
    {
      title: '文件路径',
      dataIndex: 'filePath',
      key: 'filePath',
      ellipsis: true,
    },
    {
      title: '文件大小',
      dataIndex: 'fileSize',
      key: 'fileSize',
      render: (size) => `${(size / 1024).toFixed(2)} KB`,
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_, record) => (
        <Button 
          type="primary" 
          icon={<EditOutlined />} 
          onClick={() => handleEdit(record)}
        >
          编辑
        </Button>
      ),
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Row gutter={16} align="middle">
          <Col flex="auto">
            <Input
              placeholder="输入音频文件夹路径 (如: C:\audio_files)"
              value={directory}
              onChange={(e) => setDirectory(e.target.value)}
              onPressEnter={loadDirectory}
              prefix={<FolderOpenOutlined />}
            />
          </Col>
          <Col>
            <Button 
              type="primary" 
              onClick={loadDirectory}
              loading={loading}
            >
              加载音频文件
            </Button>
          </Col>
        </Row>
      </div>

      <Table
        columns={columns}
        dataSource={audioFiles}
        loading={loading}
        pagination={{ pageSize: 10 }}
        scroll={{ y: 500 }}
        rowKey="key"
      />

      {/* 波形编辑模态框 */}
      <Modal
        title={`音频编辑 - ${editingFile?.fileName || ''}`}
        open={isWaveVisible}
        width={1000}
        onCancel={() => {
          pauseAudio();
          setIsWaveVisible(false);
        }}
        footer={[
          <Space key="controls" style={{ marginRight: 'auto' }}>
            <Button 
              type={isPlaying ? "primary" : "default"} 
              icon={isPlaying ? <PauseOutlined /> : <PlayCircleOutlined />}
              onClick={isPlaying ? pauseAudio : playFullAudio}
            >
              {isPlaying ? "暂停" : "播放全部"}
            </Button>
            <Button 
              type={isPlayingRegion ? "primary" : "default"} 
              icon={<SoundOutlined />}
              onClick={isPlayingRegion ? pauseAudio : playSelectedRegion}
              disabled={selectedRegions.length === 0}
            >
              {isPlayingRegion ? "暂停区域" : "播放选中区域"}
            </Button>
            <Button 
              icon={<StepBackwardOutlined />}
              onClick={playPrevRegion}
              disabled={selectedRegions.length < 2}
            >
              上一个
            </Button>
            <Button 
              icon={<StepForwardOutlined />}
              onClick={playNextRegion}
              disabled={selectedRegions.length < 2}
            >
              下一个
            </Button>
          </Space>,
          <Space key="actions">
            <Button 
              type="primary" 
              icon={<PlusOutlined />}
              onClick={addRegion}
              disabled={regions.length >= 5}
            >
              添加区域
            </Button>
            <Button 
              key="clip" 
              type="primary" 
              onClick={handleCompositeClip}
              loading={loading}
              disabled={selectedRegions.length === 0}
            >
              <SaveOutlined /> 组合剪辑
            </Button>
            <Button key="cancel" onClick={() => {
              pauseAudio();
              setIsWaveVisible(false);
            }}>
              <CloseOutlined /> 关闭
            </Button>
          </Space>
        ]}
        destroyOnClose
      >
        <div id="waveform" style={{ marginBottom: 24 }} />
        
        {regions.length > 0 && (
          <Collapse defaultActiveKey={['1']} style={{ marginBottom: 16 }}>
            <Panel header="剪辑区域管理" key="1">
              <div style={{ maxHeight: 200, overflowY: 'auto' }}>
                {regions.map((region, index) => (
                  <div 
                    key={region.id} 
                    style={{
                      padding: '8px 12px',
                      marginBottom: 8,
                      borderLeft: `4px solid ${region.color.replace('0.3', '1')}`,
                      backgroundColor: selectedRegions.includes(region.id) 
                        ? `${region.color.replace('0.3', '0.1')}` 
                        : '#f9f9f9',
                    }}
                  >
                    <Row align="middle">
                      <Col span={16}>
                        <Checkbox
                          checked={selectedRegions.includes(region.id)}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setSelectedRegions(prev => [...prev, region.id]);
                            } else {
                              setSelectedRegions(prev => prev.filter(id => id !== region.id));
                            }
                          }}
                        >
                          <span style={{ fontWeight: 'bold' }}>{region.content}</span>
                        </Checkbox>
                        <div style={{ marginLeft: 24, color: '#666' }}>
                          开始: {region.start.toFixed(1)}秒 | 结束: {region.end.toFixed(1)}秒 | 
                          时长: {(region.end - region.start).toFixed(1)}秒
                        </div>
                      </Col>
                      <Col span={8} style={{ textAlign: 'right' }}>
                        <Popconfirm
                          title="确定要删除这个区域吗？"
                          onConfirm={() => deleteRegion(region.id)}
                          okText="删除"
                          cancelText="取消"
                        >
                          <Button 
                            type="text" 
                            danger 
                            icon={<DeleteOutlined />}
                            size="small"
                          />
                        </Popconfirm>
                      </Col>
                    </Row>
                  </div>
                ))}
              </div>
            </Panel>
          </Collapse>
        )}
        
        {isPlayingRegion && (
          <Progress 
            percent={playbackProgress} 
            status="active" 
            strokeColor="#4F46E5"
            format={(percent) => `播放中: ${percent.toFixed(0)}%`}
          />
        )}
      </Modal>

      {/* 声纹注册表单模态框 */}
      {/* 组合剪辑预览模态框 */}
      <Modal
        title="组合剪辑预览"
        open={isFormVisible}
        width={800}
        onCancel={() => {
          pauseAudio();
          setIsFormVisible(false);
        }}
        footer={[
          <Space key="controls">
            <Button 
              type={isPlayingComposite ? "primary" : "default"} 
              icon={isPlayingComposite ? <PauseOutlined /> : <PlayCircleOutlined />}
              onClick={isPlayingComposite ? pauseAudio : playCompositeAudio}
              disabled={!compositeAudio}
            >
              {isPlayingComposite ? "暂停预览" : "播放预览"}
            </Button>
          </Space>,
          <Space key="actions">
            <Button 
              onClick={() => {
                pauseAudio();
                setIsFormVisible(false);
                setIsWaveVisible(true);
              }}
            >
              <CloseOutlined /> 返回编辑
            </Button>
            {/* <Button 
              type="primary" 
              onClick={handleRegisterComposite}
              disabled={!compositeAudio}
            >
              <SaveOutlined /> 注册声纹
            </Button> */}
            <Button 
                type="primary" 
                onClick={handleRegisterComposite}
                disabled={!clippedFile} // 使用剪辑结果作为判断条件
                >
                <SaveOutlined /> 注册声纹
            </Button>
          </Space>
        ]}
        destroyOnClose
      >
        {compositeProgress > 0 && (
          <Progress 
            percent={compositeProgress} 
            status={isPlayingComposite ? 'active' : 'normal'} 
            strokeColor="#52c41a"
          />
        )}
        
        <div style={{ margin: '20px 0', textAlign: 'center' }}>
          {compositeAudio ? (
            <Tag color="green" style={{ fontSize: 16, padding: '8px 16px' }}>
              组合剪辑完成: {clippedFile?.fileName}
            </Tag>
          ) : (
            <Tag color="orange" style={{ fontSize: 16, padding: '8px 16px' }}>
              正在处理组合剪辑...
            </Tag>
          )}
        </div>
        {/* <VoiceForm 
          form={form} 
          onSubmit={handleFormSubmit} 
          initialValues={{ fileName: clippedFile?.fileName }}
          fileUrl={clippedFile ? `${API_BASE_URL}/file?path=${encodeURIComponent(clippedFile.filePath)}` : null}
        /> */}
        <Form form={form} layout="vertical" 
            onSubmit={handleFormSubmit} 
            initialValues={{ fileName: clippedFile?.fileName }}
            fileUrl={clippedFile ? `${API_BASE_URL}/embedding/file?path=${encodeURIComponent(clippedFile.filePath)}` : null}
            >
            <Form.Item
                name="speakerName"
                label="用户名"
                rules={[{ required: true, message: '请输入用户名!' }]}
            >
                <Input />
            </Form.Item>
            <Form.Item name="userType" label="人员类型">
                <Radio.Group onChange={(e) => {
                    setUserType(e.target.value);
                }} value={userType}>
                    <Radio value="1">普通用户</Radio>
                    <Radio value="2">话务员</Radio>
                    <Radio value="3">重要用户</Radio>
                </Radio.Group>
            </Form.Item>

            <Form.Item name="option" label="选择上传方式：（上传文件和录音选一个即可）">
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
                    label="文件名"
                // rules={[{ required: true, message: '请输入用户名!' }]}
                >
                    <Input readOnly placeholder="上传或者录音后自动填充"/>
                </Form.Item>
                {playName ? <audio
                    src={'http://'+window.location.hostname+':5000/media/' + playName}
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

export default VoiceAsr;