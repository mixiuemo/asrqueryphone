import React from 'react';
import {
     Button, message, Upload, Spin
} from 'antd';
import { PlusOutlined, LoadingOutlined, CloseCircleOutlined } from '@ant-design/icons';

import moment from 'moment';
import 'moment/locale/zh-cn';
moment.locale('zh-cn');

export default class TestVoice extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            levelList: [],
            typeList: [],
            orgSelectTree: [],
            data: this.props.data || {},
            workDirectory: '',
            directionList: global.directionList,
            visible: false,
            isRecording: false,
            audioUrl: null,
            audioBlob: null,
            isUpload: true,
            fileList: [], // 用于存储上传文件列表
            uploadFileList: {},
            showName: this.props.data && this.props.data.position && this.props.data.position.file && this.props.data.position.file.response && this.props.data.position.file.response.ret || '',
            isUploading: false, // 添加一个标志
        };
        this.mediaRecorderRef = null;
    }

    componentDidMount() {
        fetch(global.ServerUrl + "media/get-current-directory", {
            method: "POST",
            headers: {
                'Content-Type': 'application/json',
            },
        })
            .then(response => {
                console.log("Response object:", response);
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json(); // 解析 JSON 格式的响应
            })
            .then(data => {
                this.setState({ workDirectory: data.directory })
                this.props.gainPathFromChild(data.directory)
                console.log("当前运行目录:", data.directory);
                // 你可以在这里处理路径
            })
            .catch(error => {
                console.error("获取当前运行目录失败:", error);
            });
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

            mediaRecorder.onstop = () => {
                const audioBlob = new Blob(audioChunks, { type: "audio/wav" });
                const audioUrl = URL.createObjectURL(audioBlob);
                this.setState({ audioUrl, audioBlob, isRecording: false, isUpload: true });
                // this.uploadAudio;
                if (!audioBlob) {
                    message.error("请先录音");
                    return;
                }
                this.setState({ isUploading: true }); // 开始上传时显示 Spin
                const formData = new FormData();
                formData.append("file", audioBlob, "recording.wav");
        
                fetch(global.ServerUrl + "media/uploadVoice", { // 替换为你的上传接口地址
                    method: "POST",
                    body: formData,
                })
                    .then((response) => response.json())
                    .then((data) => {
                        message.success("录音文件已上传识别中...").then(() => {
                            this.props.gainFileFromChild(fileAsObject.response.ret)
                            this.setState({ isUploading: false }); // 上传完成后隐藏 Spin
                        });
                        // 构建上传后的文件对象
                        const fileAsObject = {
                            uid: Date.now(), // 唯一标识符，可以使用 Date.now() 或其他唯一值
                            name: "recording.wav", // 文件名
                            status: "done", // 文件状态：done、uploading、error
                            size: audioBlob.size, // 文件大小
                            type: "audio/wav", // 文件类型
                            lastModified: Date.now(), // 文件最后修改时间
                            url: data.url || URL.createObjectURL(audioBlob), // 文件预览 URL，优先使用服务器返回的 URL
                            response: data, // 服务器返回的响应数据
                            originFileObj: new File([audioBlob], "recording.wav", { type: "audio/wav" }) // 原始文件对象
                        };
                        const uploadedFile = [{
                            uid: Date.now(), // 唯一标识符，可以使用 Date.now() 或其他唯一值
                            name: "recording.wav", // 文件名
                            status: "done", // 文件状态：done、uploading、error
                            size: audioBlob.size, // 文件大小
                            type: "audio/wav", // 文件类型
                            lastModified: Date.now(), // 文件最后修改时间
                            url: data.url || URL.createObjectURL(audioBlob), // 文件预览 URL，优先使用服务器返回的 URL
                            response: data, // 服务器返回的响应数据
                            originFileObj: new File([audioBlob], "recording.wav", { type: "audio/wav" }) // 原始文件对象
                        }];
                        const temp = {}
                        temp.file = fileAsObject;
                        temp.fileList = uploadedFile
        
                        this.setState({ showName: fileAsObject.response.ret })
                        console.log("Upload success:", data);
                    })
                    .catch((error) => {
                        message.error("录音文件上传失败");
                        console.error("Upload error:", error);
                    });
            };
        } catch (error) {
            message.error("无法访问麦克风，请检查权限设置");
            console.error("Error accessing microphone:", error);
        }
    };

    // 停止录音
    stopRecording = () => {
        if (this.mediaRecorderRef) {
            this.mediaRecorderRef.stop();
        }
    };

    // 測試录音文件
    uploadAudio = () => {

        const { audioBlob } = this.state;
        if (!audioBlob) {
            message.error("请先录音");
            return;
        }
        this.setState({ isUploading: true }); // 开始上传时显示 Spin
        const formData = new FormData();
        formData.append("file", audioBlob, "recording.wav");

        fetch(global.ServerUrl + "media/uploadVoice", { // 替换为你的上传接口地址
            method: "POST",
            body: formData,
        })
            .then((response) => response.json())
            .then((data) => {
                message.success("录音文件已上传识别中...").then(() => {
                    this.props.gainFileFromChild(fileAsObject.response.ret)
                    this.setState({ isUploading: false }); // 上传完成后隐藏 Spin
                });
                // 构建上传后的文件对象
                const fileAsObject = {
                    uid: Date.now(), // 唯一标识符，可以使用 Date.now() 或其他唯一值
                    name: "recording.wav", // 文件名
                    status: "done", // 文件状态：done、uploading、error
                    size: audioBlob.size, // 文件大小
                    type: "audio/wav", // 文件类型
                    lastModified: Date.now(), // 文件最后修改时间
                    url: data.url || URL.createObjectURL(audioBlob), // 文件预览 URL，优先使用服务器返回的 URL
                    response: data, // 服务器返回的响应数据
                    originFileObj: new File([audioBlob], "recording.wav", { type: "audio/wav" }) // 原始文件对象
                };
                const uploadedFile = [{
                    uid: Date.now(), // 唯一标识符，可以使用 Date.now() 或其他唯一值
                    name: "recording.wav", // 文件名
                    status: "done", // 文件状态：done、uploading、error
                    size: audioBlob.size, // 文件大小
                    type: "audio/wav", // 文件类型
                    lastModified: Date.now(), // 文件最后修改时间
                    url: data.url || URL.createObjectURL(audioBlob), // 文件预览 URL，优先使用服务器返回的 URL
                    response: data, // 服务器返回的响应数据
                    originFileObj: new File([audioBlob], "recording.wav", { type: "audio/wav" }) // 原始文件对象
                }];
                const temp = {}
                temp.file = fileAsObject;
                temp.fileList = uploadedFile

                this.setState({ showName: fileAsObject.response.ret })
                console.log("Upload success:", data);
            })
            .catch((error) => {
                message.error("录音文件上传失败");
                console.error("Upload error:", error);
            });
    };

    handleChange = (info) => {
        const { uploadFileList } = this.state
        this.setState({ fileList: info.fileList.slice(0, 1) });
        const { data } = this.state;
        data.position = info
        this.setState({ data: data })
        if (info.file.status === 'uploading') {
            this.setState({ loading: true, isUpload: false });
            return;
        }
        if (info.file.status === 'done') {
            if (uploadFileList.file.name) {
                this.setState({ showName: uploadFileList.fileList[0].response.ret, audioBlob: null, isUpload: false })
            } else {
                this.setState({ showName: info.file.response.ret, audioBlob: null, isUpload: false })
            }

            this.forceUpdate()
        }
    };
    handleRemove = () => {
        this.setState({ data: { position: null }, loading: false, showName: '', isUpload: true, fileList: [] }, () => {
        })
        this.forceUpdate()
    }

    // 在上传前检查是否已经有文件
    beforeUpload = (file) => {
        const { fileList } = this.state;
        if (fileList.length > 0) {
            message.error('You can only upload one file at a time.');
            return false;
        }
        return true;
    };
    render() {
        const { isRecording, audioUrl, isUploading } = this.state;
        return (
            <div style={{ marginLeft: '110px', marginBottom: '8px' }}>
                <span style={{ fontSize: 16, color: 'black' }}>测试录音：</span>
                <Button
                    type="primary"
                    onClick={this.startRecording}
                    disabled={isRecording}
                >
                    开始录音
                </Button>
                <Button
                    type="danger"
                    onClick={this.stopRecording}
                    disabled={!isRecording}
                    style={{ marginLeft: '8px' }}
                >
                    停止录音
                </Button>
                {/* <Button
                    type="success"
                    onClick={this.uploadAudio}
                    disabled={!this.state.audioBlob}
                    style={{ marginLeft: '8px' }}
                >
                    测试录音
                </Button> */}<br/>
                {audioUrl && <audio style={{ marginTop: '18px', marginLeft: '0px' }} src={audioUrl} controls />}
                <br />
                {isUploading && <Spin style={{ marginTop: '18px', marginLeft: '26%' }} size="large" />} {/* 根据 isUploading 的状态显示 Spin */}<br />
                {isUploading ? <span></span> : this.props.whoIs && <span style={{ fontSize: '18px', color: this.props.whoIs == '识别失败,当前声音未注册！' ? 'red' : 'green' }}><span>{this.props.whoIs}</span></span>} {/* 根据 whoIs 的值显示 span */}
                {/* <Spin size="large" />
                
                當前聲音為：<span>{this.props.whoIs}</span> */}
            </div>

        );
    }

}