// VoiceMicrophone.js
import React, { Component } from "react";
import grayVo from "../../assets/image/grayVo.png"; // 动态导入灰色喇叭图片
import greenVo from "../../assets/image/greenVo.png"; // 动态导入绿色喇叭图片

class VoiceMicrophone extends Component {
  constructor(props) {
    super(props);
    this.state = {
      audioLevel: 0, // 音量值
      speakerImage: grayVo, // 默认显示灰色喇叭
    };
    this.audioContext = null;
    this.analyser = null;
  }

  componentDidMount() {
    this.initAudioContext();
  }

  componentWillUnmount() {
    if (this.audioContext) {
      this.audioContext.close();
    }
  }

  initAudioContext = async () => {
    try {
      this.audioContext = new AudioContext();
      this.analyser = this.audioContext.createAnalyser();
      this.analyser.fftSize = 1024;
      this.analyser.smoothingTimeConstant = 0.8;

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const source = this.audioContext.createMediaStreamSource(stream);
      source.connect(this.analyser);

      this.startListening();
    } catch (error) {
      console.error("麦克风访问失败：", error);
    }
  };

  startListening = () => {
    const dataArray = new Uint8Array(this.analyser.frequencyBinCount);
    const updateVolume = () => {
      this.analyser.getByteTimeDomainData(dataArray);
      const volume = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;

      // 每次音量变化时切换图片
      const speakerImage = volume > this.state.audioLevel ? greenVo : grayVo;
      this.setState({ audioLevel: volume, speakerImage });

      requestAnimationFrame(updateVolume);
    };
    updateVolume();
  };

  render() {
    const { audioLevel, speakerImage } = this.state;

    return (
      <div className="volume-meter">
        <h2>音量检测</h2>
        <img
          src={speakerImage}
          alt="Speaker"
          style={{
            width: "100px",
            height: "auto",
            transition: "opacity 0.2s ease",
          }}
        />
        {/* <p>当前音量：{audioLevel.toFixed(2)}</p> */}
      </div>
    );
  }
}

export default VoiceMicrophone;