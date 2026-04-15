import React, { useEffect, useRef, useState } from 'react';
import { Card, Input, Button, Space, List, Typography, Tag, Divider, message, Segmented } from 'antd';
import config from '../config';
import { sendMqTest, sendMqTestRecord, sendMqTestTts } from '../services/api';
import './MqTest.css';

const { TextArea } = Input;
const API_BASE_URL = process.env.NODE_ENV === 'development' ? config.baseUrl.dev : config.baseUrl.pro;

const MqTest = () => {
  const [inputText, setInputText] = useState('');
  const [messages, setMessages] = useState([]);
  const [sending, setSending] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState('connecting');
  const [sentCount, setSentCount] = useState(0);
  const [recvCount, setRecvCount] = useState(0);
  const [lastLatency, setLastLatency] = useState(null);
  const [avgLatency, setAvgLatency] = useState(null);
  const [lastSeq, setLastSeq] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [inputMode, setInputMode] = useState('voice');
  const [testMode, setTestMode] = useState('full');
  const [activeStep, setActiveStep] = useState(0);
  const sendTimesRef = useRef(new Map());
  const latencySumRef = useRef(0);
  const stepTimersRef = useRef([]);
  const clientIdRef = useRef(`client_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`);
  const apiRootRef = useRef(API_BASE_URL.replace(/\/api\/?$/, ''));
  const listRef = useRef(null);
  const testModeRef = useRef('full');
  const audioCtxRef = useRef(null);
  const processorRef = useRef(null);
  const sourceRef = useRef(null);
  const streamRef = useRef(null);
  const pcmChunksRef = useRef([]);

  const clearStepTimers = () => {
    stepTimersRef.current.forEach(clearTimeout);
    stepTimersRef.current = [];
  };

  useEffect(() => {
    testModeRef.current = testMode;
  }, [testMode]);

  useEffect(() => {
    if (!listRef.current) return;
    const container = listRef.current.querySelector('.ant-list-items');
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  }, [messages]);

  const filteredMessages = messages.filter((m) => {
    if (testMode === 'asr') {
      return m.type === 'asr';
    }
    if (testMode === 'tts') {
      return m.type === 'tts' || m.type === 'user';
    }
    if (testMode === 'dialog') {
      return m.type === 'inte' || m.type === 'user' || m.role === 'user';
    }
    return true;
  });

  const latestUser = [...filteredMessages].filter(m => m.role === 'user').slice(-1)[0];
  const latestSystem = [...filteredMessages].filter(m => m.role === 'assistant' && m.type !== 'asr').slice(-1)[0];
  const latestAsr = [...filteredMessages].filter(m => m.type === 'asr').slice(-1)[0];
  const latestTts = [...filteredMessages].filter(m => m.ttsUrl).slice(-1)[0];

  const modeInfo = {
    asr: {
      label: 'ASR 单测',
      desc: '仅录音 → ASR 识别',
      input: 'voice',
      note: ''
    },
    dialog: {
      label: '交互 单测',
      desc: '文字直达 → 业务逻辑',
      input: 'text',
      note: ''
    },
    tts: {
      label: 'TTS 单测',
      desc: '文本 → TTS 合成',
      input: 'text',
      note: ''
    },
    full: {
      label: '全链路',
      desc: '录音 → ASR → 交互 → TTS',
      input: 'voice',
      note: ''
    }
  };

  useEffect(() => {
    const url = `${API_BASE_URL}/mqtest/stream?clientId=${clientIdRef.current}`;
    const es = new EventSource(url);

    es.onopen = () => {
      setConnectionStatus('open');
    };

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (testModeRef.current === 'asr' && data.type !== 'asr_result') {
          return;
        }
        if (testModeRef.current === 'dialog' && data.type !== 'inte_msg') {
          return;
        }
        if (testModeRef.current === 'tts' && data.type !== 'tts_result') {
          return;
        }
        if (data.type !== 'inte_msg' && data.type !== 'tts_result' && data.type !== 'asr_result') return;
        if (data.type === 'asr_result') {
          const asrText = data.asr_content || '';
          if (!asrText) return;
          setRecvCount(prev => prev + 1);
          if (data.seq && sendTimesRef.current.has(data.seq)) {
            const ms = Date.now() - sendTimesRef.current.get(data.seq);
            sendTimesRef.current.delete(data.seq);
            setLastLatency(ms);
            latencySumRef.current += ms;
            const avg = Math.round(latencySumRef.current / (recvCount + 1));
            setAvgLatency(avg);
          }
          clearStepTimers();
          setActiveStep(2);
          stepTimersRef.current.push(setTimeout(() => setActiveStep(0), 2500));
          if (testModeRef.current === 'full') {
            setMessages(prev => {
              const idxFromEnd = [...prev].reverse().findIndex(m => m.role === 'user' && m.type === 'user');
              if (idxFromEnd == -1) {
                return [
                  ...prev,
                  {
                    id: `user_asr_${data.seq || 'no_seq'}_${Date.now()}`,
                    role: 'user',
                    text: `\u3010\u8bed\u97f3\u3011${asrText}`,
                    type: 'user',
                    seq: data.seq,
                    channel: data.channel,
                    time: new Date().toLocaleTimeString(),
                    ts: Date.now()
                  }
                ];
              }
              const index = prev.length - 1 - idxFromEnd;
              const next = prev.slice();
              next[index] = {
                ...next[index],
                text: `\u3010\u8bed\u97f3\u3011${asrText}`
              };
              return next;
            });
            return;
          }
          setMessages(prev => [
            ...prev,
            {
              id: `asr_${data.seq || 'no_seq'}_${Date.now()}`,
              role: 'assistant',
              text: `ASR\u8bc6\u522b\uff1a${asrText}`,
              type: 'asr',
              seq: data.seq,
              channel: data.channel,
              time: new Date().toLocaleTimeString(),
              ts: Date.now()
            }
          ]);
          return;
        }
        if (data.type === 'tts_result') {
          const ttsFile = data.switch === '1' ? data.prompt_file : data.file;
          if (!ttsFile) return;
          const ttsUrl = `${config.ttsBaseUrl?.dev || ''}${ttsFile}`;
          setRecvCount(prev => prev + 1);
          if (data.seq && sendTimesRef.current.has(data.seq)) {
            const ms = Date.now() - sendTimesRef.current.get(data.seq);
            sendTimesRef.current.delete(data.seq);
            setLastLatency(ms);
            latencySumRef.current += ms;
            const avg = Math.round(latencySumRef.current / (recvCount + 1));
            setAvgLatency(avg);
          }
          clearStepTimers();
          setActiveStep(testModeRef.current === 'tts' ? 2 : testModeRef.current === 'full' ? 4 : 3);
          stepTimersRef.current.push(setTimeout(() => setActiveStep(0), 2500));
          setMessages(prev => {
            let updated = false;
            const next = prev.map((m) => {
              if (!updated && m.type === 'inte' && m.seq && m.seq === data.seq) {
                updated = true;
                return { ...m, ttsUrl };
              }
              return m;
            });
            if (!updated) {
              next.push({
                id: `tts_${data.seq || 'no_seq'}_${Date.now()}`,
                role: 'assistant',
                text: '',
                type: 'tts',
                seq: data.seq,
                channel: data.channel,
                ttsUrl,
                time: new Date().toLocaleTimeString(),
                ts: Date.now()
              });
            }
            return next;
          });
          return;
        }
        setRecvCount(prev => prev + 1);
        if (data.seq && sendTimesRef.current.has(data.seq)) {
          const ms = Date.now() - sendTimesRef.current.get(data.seq);
          sendTimesRef.current.delete(data.seq);
          setLastLatency(ms);
          latencySumRef.current += ms;
          const avg = Math.round(latencySumRef.current / (recvCount + 1));
          setAvgLatency(avg);
        }
        clearStepTimers();
        setActiveStep(3);
        stepTimersRef.current.push(setTimeout(() => setActiveStep(0), 2500));
        const formattedText = (() => {
          if (data.switch === '1') {
            const unit = data.result_unit || '';
            const name = data.result_name || '';
            const job = data.result_job || '';
            const phone = data.phone || '';
            return `帮用户转接给${unit}${name}${job}，号码是：${phone}`;
          }
          return data.text || '';
        })();

        setMessages(prev => [
          ...prev,
          {
            id: `${data.seq || 'no_seq'}_${Date.now()}`,
            role: 'assistant',
            text: formattedText,
            type: 'inte',
            seq: data.seq,
            channel: data.channel,
            file: data.file,
            raw: data.raw,
            time: new Date().toLocaleTimeString(),
            ts: Date.now()
          }
        ]);
      } catch (e) {
        // ignore parse errors
      }
    };

    es.onerror = () => {
      setConnectionStatus('error');
    };

    return () => {
      es.close();
    };
  }, []);

  const handleSend = async () => {
    if (testMode === 'tts') {
      const text = inputText.trim();
      if (!text) return;
      setSending(true);
      clearStepTimers();
      setActiveStep(0);
      stepTimersRef.current.push(setTimeout(() => setActiveStep(1), 200));
      try {
        const resp = await sendMqTestTts(text, clientIdRef.current);
        const seq = resp.seq;
        sendTimesRef.current.set(seq, Date.now());
        setSentCount(prev => prev + 1);
        setLastSeq(seq);
        setMessages(prev => [
          ...prev,
          {
            id: `user_tts_${seq}_${Date.now()}`,
            role: 'user',
            text,
            type: 'user',
            seq,
            channel: resp.channel,
            time: new Date().toLocaleTimeString(),
            ts: Date.now()
          }
        ]);
        setInputText('');
      } catch (e) {
        message.error('TTS 发送失败');
      } finally {
        setSending(false);
      }
      return;
    }
    if (inputMode !== 'text') {
      message.info('文字直达模式下才会发送文本');
      return;
    }
    const text = inputText.trim();
    if (!text) return;
    setSending(true);
    clearStepTimers();
    setActiveStep(0);
    stepTimersRef.current.push(setTimeout(() => setActiveStep(2), 180));
    try {
      const resp = await sendMqTest(text, clientIdRef.current);
      const seq = resp.seq;
      sendTimesRef.current.set(seq, Date.now());
      setSentCount(prev => prev + 1);
      setLastSeq(seq);
      setMessages(prev => [
        ...prev,
        {
          id: `user_${seq}_${Date.now()}`,
          role: 'user',
          text,
          type: 'user',
          seq,
          channel: resp.channel,
          time: new Date().toLocaleTimeString(),
          ts: Date.now()
        }
      ]);
      setInputText('');
    } catch (e) {
      setMessages(prev => [
        ...prev,
        {
          id: `system_${Date.now()}`,
          role: 'system',
          text: '发送失败，请检查后端或MQ连接状态',
          type: 'system',
          time: new Date().toLocaleTimeString(),
          ts: Date.now()
        }
      ]);
      clearStepTimers();
      setActiveStep(0);
    } finally {
      setSending(false);
    }
  };

  const handleClear = () => {
    setMessages([]);
    setSentCount(0);
    setRecvCount(0);
    setLastLatency(null);
    setAvgLatency(null);
    setLastSeq('');
    sendTimesRef.current.clear();
    latencySumRef.current = 0;
    clearStepTimers();
    setActiveStep(0);
  };

  const downsampleBuffer = (buffer, sampleRate, outRate) => {
    if (outRate === sampleRate) return buffer;
    const ratio = sampleRate / outRate;
    const newLength = Math.round(buffer.length / ratio);
    const result = new Float32Array(newLength);
    let offsetResult = 0;
    let offsetBuffer = 0;
    while (offsetResult < result.length) {
      const nextOffsetBuffer = Math.round((offsetResult + 1) * ratio);
      let accum = 0;
      let count = 0;
      for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i += 1) {
        accum += buffer[i];
        count += 1;
      }
      result[offsetResult] = accum / count;
      offsetResult += 1;
      offsetBuffer = nextOffsetBuffer;
    }
    return result;
  };

  const floatTo16BitPCM = (float32) => {
    const output = new Int16Array(float32.length);
    for (let i = 0; i < float32.length; i += 1) {
      let s = Math.max(-1, Math.min(1, float32[i]));
      output[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }
    return output;
  };

  const concatInt16 = (chunks) => {
    const totalLength = chunks.reduce((sum, arr) => sum + arr.length, 0);
    const result = new Int16Array(totalLength);
    let offset = 0;
    chunks.forEach((arr) => {
      result.set(arr, offset);
      offset += arr.length;
    });
    return result;
  };

  const int16ToBase64 = (int16) => {
    const bytes = new Uint8Array(int16.buffer);
    let binary = '';
    const chunkSize = 0x8000;
    for (let i = 0; i < bytes.length; i += chunkSize) {
      const sub = bytes.subarray(i, i + chunkSize);
      binary += String.fromCharCode.apply(null, sub);
    }
    return btoa(binary);
  };

  const startRecording = async () => {
    if (isRecording) return;
    if (testMode === 'dialog' || testMode === 'tts') {
      message.info('当前模式不需要录音');
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      audioCtxRef.current = audioCtx;
      const source = audioCtx.createMediaStreamSource(stream);
      sourceRef.current = source;
      const processor = audioCtx.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;
      pcmChunksRef.current = [];

      processor.onaudioprocess = (e) => {
        const input = e.inputBuffer.getChannelData(0);
        const downsampled = downsampleBuffer(input, audioCtx.sampleRate, 16000);
        const pcm16 = floatTo16BitPCM(downsampled);
        pcmChunksRef.current.push(pcm16);
      };

      source.connect(processor);
      processor.connect(audioCtx.destination);
      setIsRecording(true);
      clearStepTimers();
      setActiveStep(1);
      message.success('开始录音');
    } catch (err) {
      message.error('无法访问麦克风');
    }
  };

  const stopRecording = async () => {
    if (!isRecording) return;
    setIsRecording(false);
    clearStepTimers();
    setActiveStep(1);
    try {
      if (processorRef.current) processorRef.current.disconnect();
      if (sourceRef.current) sourceRef.current.disconnect();
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
      }
      if (audioCtxRef.current) await audioCtxRef.current.close();
    } catch (e) {
      // ignore
    }

    const pcm16 = concatInt16(pcmChunksRef.current);
    pcmChunksRef.current = [];
    if (pcm16.length === 0) {
      message.warning('未录到音频');
      return;
    }

    const audio_b64 = int16ToBase64(pcm16);
    setSending(true);
    clearStepTimers();
    setActiveStep(0);
    stepTimersRef.current.push(setTimeout(() => setActiveStep(1), 180));
    stepTimersRef.current.push(setTimeout(() => setActiveStep(2), 520));
    try {
      const resp = await sendMqTestRecord(audio_b64, clientIdRef.current);
      const seq = resp.seq;
      sendTimesRef.current.set(seq, Date.now());
      setSentCount(prev => prev + 1);
      setLastSeq(seq);
      setMessages(prev => [
        ...prev,
        {
          id: `user_audio_${seq}_${Date.now()}`,
          role: 'user',
          text: '【语音】已发送',
          type: 'user',
          seq,
          channel: resp.channel,
          time: new Date().toLocaleTimeString(),
          ts: Date.now()
        }
      ]);
    } catch (e) {
      setMessages(prev => [
        ...prev,
        {
          id: `system_${Date.now()}`,
          role: 'system',
          text: '录音发送失败，请检查后端或MQ连接状态',
          type: 'system',
          time: new Date().toLocaleTimeString(),
          ts: Date.now()
        }
      ]);
      clearStepTimers();
      setActiveStep(0);
    } finally {
      setSending(false);
    }
  };

  const cancelRecording = async () => {
    if (!isRecording) return;
    setIsRecording(false);
    clearStepTimers();
    setActiveStep(0);
    try {
      if (processorRef.current) processorRef.current.disconnect();
      if (sourceRef.current) sourceRef.current.disconnect();
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
      }
      if (audioCtxRef.current) await audioCtxRef.current.close();
    } catch (e) {
      // ignore
    }
    pcmChunksRef.current = [];
  };

  return (
    <div className="mqtest-shell">
      <div className="mqtest-hero">
        <div className="mqtest-hero-left">
          <Typography.Title level={3} className="mqtest-title">
            交互逻辑测试
          </Typography.Title>
          <Typography.Text className="mqtest-subtitle">
            ASR 输入 → MQ → INTE_MSG 回传，实时对话流
          </Typography.Text>
        </div>
        <div className="mqtest-hero-right">
          <Tag className={`mqtest-status mqtest-status-${connectionStatus}`}>
            {connectionStatus === 'open' ? '连接正常' : connectionStatus === 'error' ? '重连中' : '连接中'}
          </Tag>
          <div className="mqtest-meta">
            <span>主叫信息：</span>
            <span>CHANNEL=99</span>
            <span>PHONE=13800138000</span>
            <span>USERCIRCUIT=10081</span>
          </div>
        </div>
      </div>

      <div className="mqtest-workbench">
        <div className="mqtest-column">
          <Card className="mqtest-card" bordered={false}>
            <Typography.Title level={5} className="mqtest-panel-title">测试模式</Typography.Title>
            <div className="mqtest-mode-grid">
              {Object.entries(modeInfo).map(([key, item]) => (
                <div
                  key={key}
                  className={`mqtest-mode-card ${testMode === key ? 'active' : ''}`}
                  onClick={() => {
                    if (isRecording) cancelRecording();
                    handleClear();
                    setTestMode(key);
                    setInputMode(item.input);
                    setActiveStep(0);
                  }}
                >
                  <div className="mqtest-mode-title">{item.label}</div>
                  <div className="mqtest-mode-desc">{item.desc}</div>
                </div>
              ))}
            </div>
            {modeInfo[testMode].note ? (
              <div className="mqtest-note">{modeInfo[testMode].note}</div>
            ) : null}
          </Card>

          <Card className="mqtest-card" bordered={false}>
            <Typography.Title level={5} className="mqtest-panel-title">输入区</Typography.Title>
            <div className="mqtest-input">
              {testMode === 'full' ? (
                <div className="mqtest-input-switch">
                  <Segmented
                    options={[
                      { label: '语音(ASR)', value: 'voice' },
                      { label: '文字直达', value: 'text' }
                    ]}
                    value={inputMode}
                    onChange={(val) => {
                      if (isRecording) cancelRecording();
                      handleClear();
                      setInputMode(val);
                      setActiveStep(0);
                    }}
                  />
                </div>
              ) : null}
              {inputMode === 'text' && testMode !== 'asr' ? (
                <TextArea
                  rows={4}
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSend();
                    }
                  }}
                  placeholder="输入ASR内容后发送（Enter 发送 / Shift+Enter 换行）"
                />
              ) : null}
              <div className="mqtest-actions">
                {testMode !== 'asr' && inputMode === 'text' ? (
                  <>
                    <Button type="primary" onClick={handleSend} loading={sending} disabled={inputMode !== 'text'}>
                      发送
                    </Button>
                    <Button onClick={handleClear}>
                      清空
                    </Button>
                  </>
                ) : null}
                {inputMode === 'voice' ? (
                  <>
                    <Button
                      onClick={startRecording}
                      disabled={isRecording || sending || testMode === 'dialog' || testMode === 'tts'}
                      className="mqtest-btn-start"
                    >
                      开始录音
                    </Button>
                    <Button
                      onClick={stopRecording}
                      disabled={!isRecording}
                      className="mqtest-btn-stop"
                    >
                      结束录音
                    </Button>
                  </>
                ) : null}
              </div>
            </div>
          </Card>
        </div>

        <div className="mqtest-column">
          <Card className="mqtest-card" bordered={false}>
            <Typography.Title level={5} className="mqtest-panel-title">流程追踪</Typography.Title>
            <div className="mqtest-pipeline">
              {testMode === 'tts' ? (
                <>
                  <div className={`mqtest-node ${activeStep === 0 ? 'active' : ''}`}>
                    <span>等待输入</span>
                  </div>
                  <div className={`mqtest-node ${activeStep === 1 ? 'active' : ''}`}>
                    <span>语音合成</span>
                  </div>
                  <div className={`mqtest-node ${activeStep === 2 ? 'active' : ''}`}>
                    <span>TTS 回传</span>
                  </div>
                </>
              ) : (
                <>
                  <div className={`mqtest-node ${activeStep === 0 ? 'active' : ''}`}>
                    <span>等待输入</span>
                  </div>
                  {inputMode === 'voice' ? (
                    <>
                      <div className={`mqtest-node ${activeStep === 1 ? 'active' : ''}`}>
                        <span>ASR 识别</span>
                      </div>
                      {testMode === 'asr' ? (
                        <div className={`mqtest-node ${activeStep === 2 ? 'active' : ''}`}>
                          <span>ASR 回传</span>
                        </div>
                      ) : null}
                    </>
                  ) : (
                    <div className={`mqtest-node ${activeStep === 2 ? 'active' : ''}`}>
                      <span>业务处理</span>
                    </div>
                  )}
                  {testMode !== 'asr' ? (
                    <div className={`mqtest-node ${activeStep === 3 ? 'active' : ''}`}>
                      <span>INTE_MSG 回传</span>
                    </div>
                  ) : null}
                  {testMode === 'full' ? (
                    <div className={`mqtest-node ${activeStep === 4 ? 'active' : ''}`}>
                      <span>TTS 回传</span>
                    </div>
                  ) : null}
                </>
              )}
            </div>

            <Divider className="mqtest-divider" />

            <Typography.Title level={5} className="mqtest-panel-title">实时状态</Typography.Title>
            <div className="mqtest-stat-grid">
              <div className="mqtest-stat">
                <span className="mqtest-stat-label">发送数</span>
                <span className="mqtest-stat-value">{sentCount}</span>
              </div>
              <div className="mqtest-stat">
                <span className="mqtest-stat-label">回传数</span>
                <span className="mqtest-stat-value">{recvCount}</span>
              </div>
              <div className="mqtest-stat">
                <span className="mqtest-stat-label">最后SEQ</span>
                <span className="mqtest-stat-value mono">{lastSeq || '-'}</span>
              </div>
              <div className="mqtest-stat">
                <span className="mqtest-stat-label">最后延迟</span>
                <span className="mqtest-stat-value">{lastLatency !== null ? `${lastLatency} ms` : '-'}</span>
              </div>
              <div className="mqtest-stat">
                <span className="mqtest-stat-label">平均延迟</span>
                <span className="mqtest-stat-value">{avgLatency !== null ? `${avgLatency} ms` : '-'}</span>
              </div>
              <div className="mqtest-stat">
                <span className="mqtest-stat-label">连接状态</span>
                <span className={`mqtest-stat-value ${connectionStatus}`}>
                  {connectionStatus === 'open' ? '正常' : connectionStatus === 'error' ? '重连中' : '连接中'}
                </span>
              </div>
            </div>
          </Card>
        </div>

        <div className="mqtest-column">
          <Card className="mqtest-card" bordered={false}>
            <Typography.Title level={5} className="mqtest-panel-title">输出区</Typography.Title>
            <div className="mqtest-output">
              {(testMode === 'dialog' || testMode === 'full') ? (
                <div className="mqtest-output-block">
                  <div className="mqtest-output-label">最新用户输入</div>
                  <div className="mqtest-output-content">{latestUser?.text || '-'}</div>
                </div>
              ) : null}
              {testMode === 'asr' ? (
                <div className="mqtest-output-block">
                  <div className="mqtest-output-label">ASR 识别结果</div>
                  <div className="mqtest-output-content">{latestAsr?.text?.replace('ASR识别：', '') || '-'}</div>
                </div>
              ) : null}
              {testMode !== 'asr' ? (
                <div className="mqtest-output-block">
                  <div className="mqtest-output-label">最新系统回复</div>
                  <div className="mqtest-output-content">{latestSystem?.text || '-'}</div>
                </div>
              ) : null}
              {(testMode === 'tts' || testMode === 'full') ? (
                <div className="mqtest-output-block">
                  <div className="mqtest-output-label">TTS 音频</div>
                  {latestTts?.ttsUrl ? (
                    <audio controls src={latestTts.ttsUrl} />
                  ) : (
                    <div className="mqtest-output-content">-</div>
                  )}
                </div>
              ) : null}
            </div>

            <Divider className="mqtest-divider" />

            <Typography.Title level={5} className="mqtest-panel-title">对话记录</Typography.Title>
            <List
              className="mqtest-list"
              ref={listRef}
              dataSource={[...filteredMessages].sort((a, b) => {
                if (a.seq && b.seq && a.seq === b.seq) {
                  if (a.role === b.role) return a.ts - b.ts;
                  return a.role === 'user' ? -1 : 1;
                }
                return a.ts - b.ts;
              })}
              locale={{ emptyText: '暂无消息' }}
              renderItem={(item, index) => (
                <List.Item
                  className={`mqtest-item mqtest-item-${item.role}`}
                  style={{ animationDelay: `${Math.min(index * 40, 280)}ms` }}
                >
                  <div className="mqtest-rail">
                    <span className="mqtest-dot" />
                    <span className="mqtest-time">{item.time || ''}</span>
                  </div>
                  <div className="mqtest-bubble">
                    <div className="mqtest-bubble-meta">
                      <Tag color={item.role === 'user' ? 'blue' : item.role === 'assistant' ? 'green' : 'orange'}>
                        {item.role === 'user' ? '用户' : item.role === 'assistant' ? '系统' : '提示'}
                      </Tag>
                      {item.seq ? <Tag>SEQ: {item.seq}</Tag> : null}
                      {item.channel ? <Tag>CH: {item.channel}</Tag> : null}
                    </div>
                    <Typography.Text className="mqtest-bubble-text">{item.text}</Typography.Text>
                    {item.file ? (
                      <Typography.Text type="secondary" className="mqtest-bubble-file">
                        FILE: {item.file}
                      </Typography.Text>
                    ) : null}
                    {item.ttsUrl ? (
                      <div className="mqtest-tts">
                        <audio controls src={item.ttsUrl} />
                      </div>
                    ) : null}
                  </div>
                </List.Item>
              )}
            />
          </Card>
        </div>
      </div>
    </div>
  );
};

export default MqTest;
