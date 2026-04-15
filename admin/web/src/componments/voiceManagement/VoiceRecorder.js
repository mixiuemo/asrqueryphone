import React, { Component } from 'react';
import { Button, message, Modal, Input } from 'antd';
import VoiceDictaphone from './VoiceDictaphone'
import VoiceMicrophone from './VoiceMicrophone'
import { identifyVoice } from '../../services/api';
import Net from '../../services/net';
// import config from '../../../config';

const API_BASE_URL = 'http://localhost:5000/api';
//GPU-afefdbd6-2890-091e-9e66-a83b42020d05
//set CUDA_VISIBLE_DEVICES=
//CUDA_VISIBLE_DEVICES = GPU-c1f32961-38cd-d0c6-c2e3-d476f8470c4e
class VoiceRecorder extends Component {
    constructor(props) {
        super(props);
        this.state = {
            isRecording: false,
            isEnd: false,
            whoIs: '',
            tempPath: '',
            isVoiceQuery: false,
            audioLevel: 0, // 音量值
            Totaltime: 0,
        };
        this.myvad = null; // 保存 VAD 实例
        this.mediaRecorder = null; // 保存 MediaRecorder 实例
        this.audioChunks = []; // 保存录音数据
        this.mediaRecorderRef = null;
        this.analyser = null; // AnalyserNode 实例
    }

    componentDidMount() {
        console.log(window.vad)
        // 确保依赖库已经加载完成
        // this.initializeVAD();
        if (window.vad && window.ort) {
            console.log('依赖库 vad 和 ort 成功加载');
            this.initializeVAD();
        } else {
            console.error('赖库加载失败');
            if (!window.vad) console.error('vad 未定义');
            if (!window.ort) console.error('ort 未定义');
        }
        let tempPath = `${global.baseVoiceUrl}FFOutput/`
        this.setState({ tempPath: tempPath })
    }

    initializeVAD = async () => {
        let retryCount = 0;
        const maxRetries = 10;

        while (retryCount < maxRetries) {
            try {
                console.log("初始化 VAD...");
                let url = 'http://localhost:5000/vad/'
                var myvad = await window.vad.MicVAD.new({
                    baseAssetPath: url,
                    onSpeechStart: () => {
                        console.log("检测到语音开始");
                        if (this.state.isRecording) return;
                        if (this.state.isEnd) return;
                        this.setState({ isRecording: true }, () => {
                            this.startRecording();
                        });
                    },
                    onSpeechEnd: (audio) => {
                        console.log("检测到语音结束", audio);
                        this.setState({ isRecording: false, isEnd: true }, () => {
                            this.stopRecording();
                        });
                    },
                    positiveSpeechThreshold: 0.30,
                    negativeSpeechThreshold: 0.30,
                    minSpeechFrames: 8,
                    preSpeechPadFrames: 10,
                });
                console.log('VAD 初始化成功');
                myvad.start();
                this.myvad = myvad;
                return; // 初始化成功，退出循环
            } catch (error) {
                console.error('初始化 VAD 失败:', error);
                retryCount++;
                if (retryCount >= maxRetries) {
                    message.error('初始化语音检测失败，请检查依赖库');
                }
            }
        }
    };

    // 请求麦克风权限并开始录音
// 请求麦克风权限并开始录音
startRecording = async () => {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mediaRecorder = new MediaRecorder(stream);

        this.mediaRecorderRef = mediaRecorder;
        mediaRecorder.start();
        this.setState({ isRecording: true });

        const audioChunks = [];
        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
                console.log('收集到音频数据，大小:', event.data.size);
            }
        };

        mediaRecorder.onstop = async () => {
            if (audioChunks.length === 0) {
                console.error('未收集到音频数据');
                message.error("录音失败，未收集到音频数据");
                return;
            }

            const audioBlob = new Blob(audioChunks, { type: "audio/wav" });
            const audioUrl = URL.createObjectURL(audioBlob);
            this.setState({ audioUrl, audioBlob, isRecording: false, isUpload: true });

            const file = new File([audioBlob], 'recorded-audio.wav', { type: 'audio/wav' });
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
                    // message.success(`录音文件上传成功，共导入 ${data.imported} 条记录`);

                    const uploadedFileName = data.fileName || 'recorded-audio.wav';

                    // 替换文件路径中的正斜杠为反斜杠
                    const windowsFilePath = data?.file_path?.replace(/\/+/g, '\\\\');

                    // 调用后端接口
                    fetch('http://127.0.0.1:5004/identify', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            file_path: windowsFilePath  // 使用后端返回的文件路径
                        })
                    })
                        .then(response => response.json())
                        .then(async data => { // 将回调函数定义为 async
                            
                            const result = await identifyVoice(data.embedding);
                            console.log('接口返回数据:', data,result)
                            // message.info(`识别结果：${data.username}，处理时间：${data.time}秒`);
                            this.setState({ whoIs: result.result, Totaltime: data.time });
                        })
                        .catch(error => {
                            console.error('接口调用失败:', error);
                            message.error('识别失败，请重试');
                        });
                } else {
                    message.error('录音文件上传失败，服务器返回错误');
                }
            } catch (error) {
                message.error('录音文件上传失败，请重试');
                console.error('Upload error:', error);
            }
        };

        this.mediaRecorderRef = mediaRecorder;
    } catch (error) {
        message.error("无法访问麦克风，请检查权限设置");
        console.error("Error accessing microphone:", error);
    }
};

    handleButtonClick = async (fileName) => {
        // this.setState({ startTime: new Date() });

        const { tempPath } = this.state;

        const postData = {
            file_path: tempPath + fileName
        };
        try {
            let data;
            try {
                const url = global.ServerUrl + "ai/identifyVoice";
                let startTime = new Date()
                // Net.post(url, postData, async (res3) => {
                //     if (res3.result == 200) {
                //         data = res3.ret
                //         // 第二次请求
                //         const record = { currentVector: data.embedding };
                //         const uploadResponse = await fetch(global.ServerUrl + "media/identifyVoice", {
                //             method: "POST",
                //             headers: {
                //                 "Content-Type": "application/json"
                //             },
                //             body: JSON.stringify({ param: record })
                //         });

                //         if (!uploadResponse.ok) {
                //             throw new Error("请求失败，状态码：" + uploadResponse.status);
                //         }

                //         const uploadData = await uploadResponse.json();
                //         this.setState({ whoIs: uploadData.result, Totaltime: (new Date() - startTime) / 1000 });
                //         console.log("Upload success:", uploadData);
                //         this.forceUpdate()
                //     } else {
                //         console.log("识别失败")
                //     }
                // })
                // data.generateAudio = res.filename
                this.forceUpdate()
                // })

            } catch (error) {
                this.setState({ error: error.message });
                console.error('Error:', error);
            }
        } catch (error) {
            this.setState({ error: error.message });
            console.error('Error:', error);
        }
    };

    stopRecording = () => {
        console.log('停止录音...');
        if (this.mediaRecorderRef) {
            this.mediaRecorderRef.stop();
        }
    };

    componentWillUnmount() {
        // 确保在组件卸载时停止录音并释放资源
        this.stopRecording();
        if (this.myvad) {
            this.myvad.destroy();
        }
    }

    render() {
        const { whoIs, isVoiceQuery, audioLevel, Totaltime } = this.state
        return (
            <div style={{ width: '' }}>
                <Input style={{ width: '700px', hight: '200px', color: 'green' }} type="text" disabled={true} placeholder="你好，我要开始测试，床前明月光，疑是地上霜，举头望明月，低头思故乡！" />
                <div style={{ marginLeft: '600px', display: 'flex' }}>
                    {/* <VoiceMicrophone /> */}
                </div>
                <span style={{ color: '', fontSize: '18px' }}>语音活动检测</span>
                {this.state.isRecording ? <p style={{ color: 'green', fontSize: '18px' }}>正在录音...</p> : <p style={{ color: 'red', fontSize: '18px' }}>等待语音...</p>}
                <span style={{ fontSize: '18px', color: whoIs == '识别失败,当前声音未注册！' ? 'red' : 'green' }}><span>{whoIs}</span></span><br /> {/* 根据 whoIs 的值显示 span */}
                {whoIs != '' ? <span style={{ fontSize: '18px', color: 'green' }}><span>总用时：{Totaltime}s</span><br /></span> : <span></span>}
                {/* {whoIs != '识别失败,当前声音未注册！' && whoIs != '' ?
                    <Button
                        type="primary"
                        onClick={() => { this.setState({ isVoiceQuery: true }) }}
                    >
                        进入语言提问环节
                    </Button>
                    :
                    <div></div>
                } */}
                <Modal
                    title={'识别通过可进行语音查询'}
                    open={isVoiceQuery}
                    maskClosable={false}
                    width={1000}
                    destroyOnClose
                    onOk={() => { this.setState({ isVoiceQuery: false }) }}
                    onCancel={() => { this.setState({ isVoiceQuery: false }) }}
                    footer={[
                        <Button key="back" onClick={() => { this.setState({ isVoiceQuery: false }) }}>
                            关闭
                        </Button>,
                        <Button key="submit" type="primary" onClick={() => { this.setState({ isVoiceQuery: false }) }}>
                            完成
                        </Button>
                    ]}
                >
                    <VoiceDictaphone />

                </Modal>
            </div>
        );
    }
}

export default VoiceRecorder;