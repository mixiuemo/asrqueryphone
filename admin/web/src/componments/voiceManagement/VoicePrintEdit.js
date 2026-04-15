import React from 'react';
import {
    Form, Input, Select, TreeSelect, InputNumber, Modal, Button, message, Upload
} from 'antd';
import { PlusOutlined, LoadingOutlined, CloseCircleOutlined, UploadOutlined } from '@ant-design/icons';
import moment from 'moment';
import 'moment/locale/zh-cn';
moment.locale('zh-cn');

class VoicePrintEdit extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            levelList: [],
            typeList: [],
            orgSelectTree: [],
            data: this.props.data || {},
            lvList: [
                {
                    name: '1级'
                },
                {
                    name: '2级'
                },
                {
                    name: '3级'
                },
                {
                    name: '4级'
                },
                {
                    name: '5级'
                }
            ],
            level: '1级',
            directionList: global.directionList,
            visible: false,
            isRecording: false,
            audioUrl: null,
            audioBlob: null,
            isUpload: true,
            fileList: [], // 用于存储上传文件列表
            uploadFileList: {},
            showName: this.props.data && this.props.data.position && this.props.data.position.file && this.props.data.position.file.response && this.props.data.position.file.response.ret || '',
        };
        this.mediaRecorderRef = null;
    }

    componentDidMount() {
        const { data } = this.state
        console.log('', this.props)
        if (data && data.position && data.position.fileList && data.position.fileList.length) {
            this.setState({ fileList: data.position.fileList.slice(0, 1), uploadFileList: data.position })
        } else if (this.props.type == "add") {

        } else {
            this.setState({
                fileList: [
                    {
                        "uid": 1740559431214,
                        "name": data && data.number,
                        "status": "done",
                        "size": 70446,
                        "type": "audio/wav",
                        "lastModified": 1740559431214,
                        "url": "blob:http://localhost:3020/c58a1b95-49ad-4595-bd88-a86fd3d204fc",
                        "response": {
                            "result": 0,
                            "ret": data && data.number
                        },
                        "originFileObj": {}
                    }
                ]
            })

        }
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
                this.setState({ audioUrl, audioBlob, isRecording: false, isUpload: true }, () => {
                    this.uploadAudio();
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

    // 上传录音文件
    uploadAudio = () => {
        const { audioBlob } = this.state;
        if (!audioBlob) {
            message.error("请先录音");
            return;
        }

        const formData = new FormData();
        formData.append("file", audioBlob, "recording.wav");

        fetch(global.ServerUrl + "media/uploadVoice", { // 替换为你的上传接口地址
            method: "POST",
            body: formData,
        })
            .then((response) => response.json())
            .then((data) => {
                message.success("录音文件上传成功");
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
                this.props.handleValueFromChild(temp, audioBlob)
                this.setState({ showName: fileAsObject.response.ret })
                // 如果需要在组件加载时设置表单字段的值
                if (this.form) {
                    this.form.setFieldsValue({
                        number: fileAsObject.response.ret,
                    });
                }
                this.forceUpdate();
                // this.props.handleValueFromChild(uploadedFile)
                console.log("Upload success:", data);
            })
            .catch((error) => {
                message.error("录音文件上传失败");
                console.error("Upload error:", error);
            });
    };
    handleChange = (info) => {
        // this.setState({ fileList: info.fileList });
        const { uploadFileList } = this.state
        if (info.fileList.length > 1) {
            // uploadFileList
            this.setState({ uploadFileList: uploadFileList }, () => { this.props.handleValueFromChild(this.state.uploadFileList, null) });
        } else {
            this.setState({ uploadFileList: info }, () => { this.props.handleValueFromChild(this.state.uploadFileList, null) });
        }
        this.setState({ fileList: info.fileList.slice(0, 1) });
        const { data } = this.state;
        data.position = info
        this.setState({ data: data })
        if (info.file.status === 'uploading') {
            this.setState({ loading: true, isUpload: false });
            return;
        }
        if (info.file.status === 'done') {
            console.log(uploadFileList.file)
            if (uploadFileList.file.name) {
                this.setState({ showName: info.fileList[0].response.ret, audioBlob: null, isUpload: false })
            } else {
                this.setState({ showName: info.file.response.ret, audioBlob: null, isUpload: false })
            }
            if (this.form) {
                this.form.setFieldsValue({
                    number: info.file.response.ret,
                });
            }
            this.forceUpdate()
        }
    };
    onPreview = (file) => {
        // 如果文件有远程 URL，直接在新窗口打开
        if (file.response && file.response.ret) {
            const filePath = `${global.baseVoiceUrl}FFOutput/${file.response.ret}`;
            // window.open(filePath, '_blank');
            // 打开 Modal
            Modal.info({
                title: '文件预览',
                content: (
                    <div>
                        <audio controls autoPlay>
                            <source src={filePath} type="audio/mpeg" />
                            您的浏览器不支持音频播放。
                        </audio>
                    </div>
                ),
                width: 600, // 设置弹窗宽度
            });
        } else {
            console.error('文件未上传成功或响应数据无效');
        }
    }
    handleRemove = () => {
        this.setState({ data: { position: null }, loading: false, showName: '', isUpload: true, fileList: [] }, () => {
        })
        this.forceUpdate()
    }

    // 在上传前检查是否已经有文件
    beforeUpload = (file) => {
        const { fileList } = this.state;
        if (fileList.length > 0) {
            message.error('只允许上传一个文件');
            return false;
        }
        return true;
    };
    render() {
        const { levelList, lvList, typeList, numbers, isRecording, audioUrl, showName, audioBlob, data, isUpload, fileList } = this.state;
        const formItemLayout = {
            labelCol: { span: 5 },
            wrapperCol: { span: 16 }
        };
        // const data = this.props.data || {};
        // data.position=this.props.data.position?this.props.data.position:{}
        return (
            <Form layout="horizontal"
                ref={inst => this.form = inst}
                initialValues={{
                    name: this.props.data.name,
                    position: this.props.data.position,
                    number: showName,
                    desc: this.props.data.desc
                }}>
                <Form.Item label="用户名" name="name" rules={[{ required: true, message: '请输入用户名!' }]} style={{ marginLeft: '40px' }} {...formItemLayout}>
                    <Input type="text" placeholder="请输入用户名" />
                </Form.Item>

                <Form.Item label="用户名" name="name" rules={[{ required: true, message: '请输入用户名!' }]} style={{ marginLeft: '40px' }} {...formItemLayout}>
                    <Input type="text" placeholder="请输入用户名" />
                </Form.Item>

                {audioBlob == null ?
                    <Form.Item label="录音上传" name="position" style={{ marginLeft: '40px' }} {...formItemLayout}>
                        <Upload
                            accept=".audio/*,.wav,.mp3"
                            action={global.ServerUrl + "media/uploadVoice"}
                            name='file'
                            // listType="file"
                            // className="avatar-uploader"
                            // showUploadList={false}
                            fileList={fileList}
                            beforeUpload={this.beforeUpload}
                            onChange={this.handleChange}
                            onRemove={() => this.handleRemove()} // 添加移除功能
                            onPreview={this.onPreview}//增加预览功能
                        >
                            <Button>
                                <UploadOutlined /> 录音上传
                            </Button>
                        </Upload>
                    </Form.Item> : <div></div>}
                {isUpload ? <div style={{ marginLeft: '110px', marginBottom: '8px' }}>

                    <span style={{ fontSize: 16, color: 'black' }}>自主录音：</span>
                    <Button
                        type="primary"
                        onClick={this.startRecording}
                        disabled={isRecording}
                    >
                        开始录音
                    </Button>
                    <Button
                        // type="primary" 
                        // danger
                        onClick={this.stopRecording}
                        disabled={!isRecording}
                        style={{ marginLeft: '8px', background: isRecording ? 'red' : '' }}
                    >
                        停止录音
                    </Button><br />
                    {/* <Button
                        onClick={this.uploadAudio}
                        disabled={!this.state.audioBlob}
                        style={{ marginLeft: '8px' }}
                    >
                        上传录音
                    </Button> */}
                    {audioUrl && <audio style={{ marginTop: '18px', marginLeft: '30px' }} src={audioUrl} controls />}
                </div> : <div></div>}
                <Form.Item label="录音提示" style={{ marginLeft: '40px' }} {...formItemLayout}>
                    {
                        <Input.TextArea type="text" disabled={true} placeholder="你好，现在我开始注册声音，床前明月光，疑是地上霜，举头望明月，低头思故乡！" />
                    }
                </Form.Item>
                <Form.Item label="文件上传名" name="number" style={{ marginLeft: '40px' }} {...formItemLayout}>
                    <Input placeholder="自动填充文件上传名" value={showName} readOnly />
                </Form.Item>
                <Form.Item label="备注" name="desc" style={{ marginLeft: '40px' }} {...formItemLayout}>
                    <Input.TextArea type="text" placeholder="请输入备注" />
                </Form.Item>

            </Form>

        );
    }

}

export default VoicePrintEdit;