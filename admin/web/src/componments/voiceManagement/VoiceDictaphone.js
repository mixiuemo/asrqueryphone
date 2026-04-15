
import React, { Component } from 'react';
import { Button, message, Modal } from 'antd';
import Net from '../../services/net';
import { generateAudioToTxt, queryAIModal, generateAudio } from '../../services/api';
const API_BASE_URL = 'http://localhost:5000/api';
// const templateUrl = process.env.NODE_ENV === 'development' ? config.templateUrl.dev : config.templateUrl.pro;
class VoiceDictaphone extends Component {
    constructor(props) {
        super(props);
        this.state = {
            isRecording: false,
            isEnd: false,
            whoIs: '',
            tempPath: '',
            voiceText: '',
            questionArray: '',
            answerArray: '',
            isPlaying: false, // 添加一个状态，用于控制语音播放
            ttsVoiceFileName: '',
        };
        this.myvad = null; // 保存 VAD 实例
        this.mediaRecorder = null; // 保存 MediaRecorder 实例
        this.audioChunks = []; // 保存录音数据
        this.mediaRecorderRef = null;
        this.audioRef = React.createRef(); // 创建一个音频引用
    }

    componentDidMount() {
        // 
    }


    playAudio = () => {
        const { ttsVoiceFileName } = this.state;
        if (ttsVoiceFileName) {
            const audioUrl = `${global.BaseVirtualUrl}${ttsVoiceFileName}`;
            this.audioRef.current.src = audioUrl; // 设置音频源
            this.audioRef.current.play() // 播放音频
                .catch((error) => {
                    console.error("自动播放失败:", error);
                    message.error("自动播放失败，请手动播放");
                });
        }
    };

    // 处理输入框变化
    handleInputChange = (e) => {
        this.setState({ voiceText: e.target.value });
    };

    // 播放语音
    speakText = () => {
        const { voiceText } = this.state;
        if ('speechSynthesis' in window) {
            const utterance = new SpeechSynthesisUtterance(voiceText);
            utterance.lang = 'zh-CN'; // 设置语言为中文
            utterance.pitch = 1
            utterance.rate = 0.6
            window.speechSynthesis.speak(utterance);
        } else {
            alert('您的浏览器不支持文字转语音功能');
        }
    };
    stopSpeakText = () => {
        this.audioRef.current.pause() // 播放音频
    }
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
                audioChunks.push(event.data);
            };

            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(audioChunks, { type: "audio/wav" });
                const audioUrl = URL.createObjectURL(audioBlob);
                this.setState({ audioUrl, audioBlob, isRecording: false, isUpload: true, audioBlobD: audioChunks[0].size });
                if (!audioBlob) {
                    message.error("请先录音");
                    return;
                }
                const formData = new FormData();
                formData.append("file", audioBlob, "recording.wav");

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
                        // const windowsFilePath = data?.file_path?.replace(/\/+/g, '\\\\');
                        debugger
                        console.log('哈哈哈1', data?.file_path)
                        this.handleButtonClick(data?.file_path)
                            // 调用后端接口
                            // fetch('http://127.0.0.1:5004/identify', {
                            //     method: 'POST',
                            //     headers: {
                            //         'Content-Type': 'application/json',
                            //     },
                            //     body: JSON.stringify({
                            //         file_path: windowsFilePath  // 使用后端返回的文件路径
                            //     })
                            // })
                            .then(response => response.json())
                            .then(async data => { // 将回调函数定义为 async
                                debugger

                                // const result = await identifyVoice(data.embedding);
                                debugger
                                console.log('接口返回数据:', data)
                                // message.info(`识别结果：${data.username}，处理时间：${data.time}秒`);
                                // this.setState({ whoIs: result.result, Totaltime: data.time });
                            })
                            .catch(error => {
                                console.error('接口调用失败:', error);
                                // message.error('识别失败，请重试');
                            });
                    } else {
                        message.error('录音文件上传失败，服务器返回错误');
                    }
                } catch (error) {
                    message.error('录音文件上传失败，请重试');
                    console.error('Upload error:', error);
                }
            };
        } catch (error) {
            message.error("无法访问麦克风，请检查权限设置");
            console.error("Error accessing microphone:", error);
        }
    };
    handleButtonClick = async (fileName) => {
        const { tempPath } = this.state;
        let tempFile = tempPath + fileName;
        const normalizedPath = tempFile.replace(/[\\/]+/g, '/');
        console.log('哈哈哈2', normalizedPath);
        const data = {
            file_path: normalizedPath
        };
    
        try {
            // 语音转文字
            const audioToTxtData = await generateAudioToTxt(data);
            if (audioToTxtData.result === 200) {
                this.setState({ questionArray: audioToTxtData.ret.asrResult });
    
                // 查询AI大模型
                const queryAIModalData = await queryAIModal({query_text:audioToTxtData.ret.asrResult});
                if (queryAIModalData.result === 200) {
                    let cleanedText = queryAIModalData.ret.response.replace(/\s+/g, ' ');
                    cleanedText = cleanedText.trim();
                    cleanedText = cleanedText.replace(/<think>.*?<\/think>/gi, '');
                    this.setState({ voiceText: cleanedText });
    
                                let name = String(new Date().getTime() + "audio")
                                const datas = {
                                    gen_text: cleanedText,
                                    file_uuid: name,
                                    voice: 'zf_xiaoxiao.pt',
                                    speed: 1,
                                }

                    // 合成音频
                    const generateAudioData = await generateAudio(datas);
                    if (generateAudioData.result === 200) {
                        this.setState({ ttsVoiceFileName: generateAudioData.filename }, () => {
                            this.playAudio();
                        });
                    } else {
                        console.log("合成失败");
                    }
                } else {
                    console.log("AI模型查询失败");
                }
            } else {
                console.log("语音转文字失败");
            }
        } catch (error) {
            this.setState({ error: error.message });
            console.error('Error:', error);
        }
    };
    // handleButtonClick = async (fileName) => {
    //     const { tempPath } = this.state;
    //     let tempFile = tempPath + fileName
    //     // 将双反斜杠替换为单斜杠
    //     const normalizedPath = tempFile.replace(/[\\/]+/g, '/');
    //     console.log('哈哈哈2', normalizedPath)
    //     const data = {
    //         file_path: normalizedPath
    //     }
    //     try {
    //         const process_audio_url = API_BASE_URL + "/generateAudioToTxt";
    //         Net.post(process_audio_url, data, (res) => {
    //             debugger
    //             if (res.result == 200) {
    //                 this.setState({ questionArray: res.ret.asrResult })
    //                 const query_text = res.ret.asrResult
    //                 const queryAIModal_url = API_BASE_URL + "/queryAIModal";
    //                 Net.post(queryAIModal_url, { query_text: query_text }, (res2) => {
    //                     if (res2.result == 200) {
    //                         let cleanedText = res2.ret.response.replace(/\s+/g, ' '); // 将所有空白字符替换为单个空格
    //                         cleanedText = cleanedText.trim(); // 去除首尾空格
    //                         cleanedText = cleanedText.replace(/<think>.*?<\/think>/gi, '');
    //                         this.setState({ voiceText: cleanedText });
    //                         let name = String(new Date().getTime() + "audio")
    //                         const datas = {
    //                             gen_text: cleanedText,
    //                             file_uuid: name,
    //                             voice: 'zf_xiaoxiao.pt',
    //                             speed: 1,
    //                         }
    //                         const url = API_BASE_URL + "/generateAudio";
    //                         Net.post(url, datas, (res3) => {
    //                             if (res3.result == 200) {
    //                                 this.setState({ ttsVoiceFileName: res3.filename }, () => {
    //                                     // this.speakText
    //                                     this.playAudio()
    //                                 });
    //                                 this.forceUpdate()
    //                             } else {
    //                                 console.log("合成失败")
    //                             }
    //                         })
    //                         // data.generateAudio = res.filename
    //                         this.forceUpdate()
    //                     } else {
    //                         console.log("合成失败")
    //                     }
    //                 })

    //                 // })
    //                 // data.generateAudio = res.filename
    //                 this.forceUpdate()
    //             } else {
    //                 console.log("合成失败")
    //             }
    //         })

    //     } catch (error) {
    //         this.setState({ error: error.message });
    //         console.error('Error:', error);
    //     }
    // };
    stopRecording = () => {
        console.log('哈哈哈停止录音...');
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
        const { whoIs, isRecording, questionArray, ttsVoiceFileName } = this.state
        return (
            <div>
                <Button
                    type="primary"
                    onClick={this.startRecording}
                    disabled={isRecording}
                >
                    开始提问
                </Button>
                <Button
                    // type="danger"
                    onClick={this.stopRecording}
                    disabled={!isRecording}
                    style={{ marginLeft: '8px' }}
                >
                    提交问答
                </Button>
                {/* <span style={{ color: '', fontSize: '18px' }}>查询语检测</span> */}
                {this.state.isRecording ? <p style={{ color: 'green', fontSize: '18px' }}>正在录音...</p> : <p style={{ color: 'red', fontSize: '18px' }}>等待语音...</p>}
                <span style={{ fontSize: '18px', color: whoIs == '识别失败,当前声音未注册！' ? 'red' : 'green' }}><span>{whoIs}</span></span>
                <h1>查询结果转语音</h1>
                <div style={{ width: '100%', display: 'flex' }}>
                    <div style={{ width: '30%' }}>
                        问题：{questionArray}
                    </div>
                    <div style={{ width: '70%' }}>
                        <Button type="primary" onClick={this.playAudio}>播放结果</Button><Button type="primary" style={{ marginLeft: '10px' }} onClick={this.stopSpeakText}>停止播放</Button><br />
                        <audio ref={this.audioRef} controls style={{ marginTop: '10px' }}>
                            <source src={`${global.BaseVirtualUrl}${ttsVoiceFileName}`} type="audio/mpeg" />
                            Your browser does not support the audio element.
                        </audio>
                        <textarea
                            style={{ width: '400px', height: '400px' }}
                            value={this.state.voiceText}
                            onChange={this.handleInputChange}
                            placeholder="查询结果"
                        />
                    </div>
                </div>


            </div>
        );
    }
}

export default VoiceDictaphone;