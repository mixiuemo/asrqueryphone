import soundfile as sf
import os
# 1. 屏蔽进度条（尤其 TTS 推理时经常有 tqdm）
os.environ["TQDM_DISABLE"] = "1"
# 2. 强制实时刷新日志
os.environ["PYTHONUNBUFFERED"] = "1"
import sys
from pathlib import Path
sys.path.append('../../common')
from rabbitmq import RabbitMQ 
from kokoro import KPipeline, KModel
import re
from pydub import AudioSegment
import configparser
import time
import torch
from utils.loggeruitls import Logger
from flask import Flask, jsonify, send_from_directory, abort
import threading
log = Logger() 


# 加载模型
BASE_DIR = Path(__file__).resolve().parent
V11_DIR = BASE_DIR / 'Kokoro-82M-v1.1-zh'
MODEL_PATH = V11_DIR / 'kokoro-v1_1-zh.pth'
CONFIG_PATH = V11_DIR / 'config.json'
VOICE_PATH = str(V11_DIR / 'voices' / 'zf_xiaoxiao.pt')

device = 'cuda' if torch.cuda.is_available() else 'cpu'
model = KModel(model=str(MODEL_PATH), config=str(CONFIG_PATH)).to(device).eval()

# Follow make_zh.py behavior: English G2P callable + speed scheduling
en_pipeline = KPipeline(lang_code='a', repo_id='hexgrad/Kokoro-82M-v1.1-zh', model=False)
def en_callable(text):
    if text == 'Kokoro':
        return 'kˈOkəɹO'
    elif text == 'Sol':
        return 'sˈOl'
    return next(en_pipeline(text)).phonemes

def speed_callable(len_ps):
    speed = 0.8
    if len_ps <= 83:
        speed = 1
    elif len_ps < 183:
        speed = 1 - (len_ps - 83) / 500
    return speed * 1.1

pipeline = KPipeline(lang_code='z', repo_id='hexgrad/Kokoro-82M-v1.1-zh', model=model, en_callable=en_callable)

# Flask应用
app = Flask(__name__)


# 读取配置文件获取TTS_WAV_ROOT
config = configparser.ConfigParser()
config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../etc/config.ini'))
config.read(config_path, encoding='utf-8')
output_dir = config.get('MEDIA', 'TTS_WAV_ROOT').replace('\\', os.sep).replace('\\', os.sep)
if not os.path.exists(output_dir):
    os.makedirs(output_dir)
print(output_dir)

def split_text_by_length(text, max_length=100):
    """文本分割函数，每max_length个字分行"""
    if len(text) <= max_length:
        return [text]

    punctuation_priority = ['。', '？', '！', '，', '；']

    result = []
    current_text = text

    while len(current_text) > max_length:
        split_pos = max_length
        best_punct_pos = -1

        for punct in punctuation_priority:
            punct_pos = current_text.rfind(punct, 0, max_length)
            if punct_pos > best_punct_pos:
                best_punct_pos = punct_pos

        if best_punct_pos > 0:
            split_pos = best_punct_pos + 1
        else:
            split_pos = max_length

        segment = current_text[:split_pos].strip()
        if segment:
            result.append(segment)

        current_text = current_text[split_pos:].strip()

    if current_text:
        result.append(current_text)

    return result

def synthesize_audio(processed_text, voice_path=VOICE_PATH, speed=speed_callable, max_length=100):
    """分段合成并拼接音频"""
    text_segments = split_text_by_length(processed_text, max_length=max_length)
    all_audio_segments = []

    for segment in text_segments:
        if not segment.strip():
            continue

        segment_with_newline = segment + '\n'
        generator = pipeline(
            segment_with_newline,
            voice=voice_path,
            speed=speed, split_pattern=r'\n+'
        )

        segment_audio = None
        for _, _, audio in generator:
            if segment_audio is None:
                segment_audio = audio
            else:
                segment_audio = torch.cat([segment_audio, audio], dim=0)

        if segment_audio is not None:
            all_audio_segments.append(segment_audio)

    if not all_audio_segments:
        return None

    if len(all_audio_segments) == 1:
        return all_audio_segments[0]
    return torch.cat(all_audio_segments, dim=0)

# 静态访问TTS输出目录
def _safe_audio_filename(name: str) -> bool:
    # 只允许简单文件名，防止目录穿越
    if not name or name != os.path.basename(name):
        return False
    # 仅允许wav
    return name.lower().endswith(".wav")

@app.route('/tts/audio/<path:filename>', methods=['GET'])
def get_tts_audio(filename):
    if not _safe_audio_filename(filename):
        abort(404)
    return send_from_directory(output_dir, filename, mimetype='audio/wav', as_attachment=False)
# 号码播报处理
def format_phone_number(text):
    digit_to_chinese = {
        '0': '零', '1': '幺', '2': '二', '3': '三', '4': '四',
        '5': '五', '6': '六', '7': '七', '8': '八', '9': '九'
    }
    def format_digits(match):
        digits = match.group()
        if len(digits) == 12:
            digits = digits[1:]
            formatted = f"{digits[:3]}。。。{digits[3:7]}。。。{digits[7:]}"
        elif len(digits) == 11:
            formatted = f"{digits[:3]}。。。{digits[3:7]}。。。{digits[7:]}"
        elif len(digits) == 13:
            digits = digits[2:]
            formatted = f"{digits[:3]}。。。{digits[3:7]}。。。{digits[7:]}"
        elif len(digits) == 6:
            formatted = f"{digits[:3]}。。。{digits[3:]}"
        elif len(digits) == 9:
            formatted = f"{digits[:4]}。。。{digits[4:]}"
        elif len(digits) == 10:
            formatted = f"{digits[:4]}。。。{digits[4:7]}。。。{digits[7:]}"
        else:
            return ''.join(digit_to_chinese[d] for d in digits)
        
        chinese_formatted = '。。。'.join(
            ''.join(digit_to_chinese[d] for d in part)
            for part in formatted.split('。。。')
        )
        return chinese_formatted

    text = re.sub(r'\d{6,}', format_digits, text)
    text = re.sub(r'\d+', lambda m: ''.join(digit_to_chinese[d] for d in m.group()), text)
    return text



def handle_message(ch, method, properties, body):
    
    try:
        msg_str = body.decode()
        ignored_prefixes = ["HEARTBEAT:ASR", "HEARTBEAT:VOICECARD","ASR_MSG","RECORD","INTERACTION_START",
                            "AI114_TTS_RESULT","HOTWORD","HEARTBEAT:PLATFORMSERVER","HANGUP","VOICECARD_START",
                            "UpdateAi114Config","语音卡录音程序"]
        if any(msg_str.startswith(prefix) for prefix in ignored_prefixes):
            return
        msg_str = msg_str[len("INTE_MSG:"):] 
        parts = msg_str.split(":")
        data = {}
        for item in parts:
            if '=' in item:
                key, value = item.split('=', 1)
                data[key.strip()] = value.strip()
            else:
                log.warning(f"跳过无法解析的字段: {item}")
        log.info("解析后字段内容:", data)
        channelNumber_id = data.get("CHANNEL", "")
        requestID = data.get("SEQ", "")
        sysfilename = data.get("FILE", "")
        TELE_CODE = data.get("PHONE", "")
        text = data.get("TEXT", "") 
        SWITCH = data.get("SWITCH", 0) 
        CALLER = data.get("CALLER", "") 
        CALL_NAME = data.get("CALL_NAME", "") 
        CALL_JOB = data.get("CALL_JOB", "") 
        CALL_UNIT = data.get("CALL_UNIT", "")  
        RESULT_UNIT = data.get("RESULT_UNIT", "")  
        RESULT_NAME = data.get("RESULT_NAME", "")  
        RESULT_JOB = data.get("RESULT_JOB", "")  
        log.info("TTS服务收到消息: 通道号为:",channelNumber_id,"完整消息内容为:",body.decode())
        
        # 只有当sysfilename和text都不为空时，才生成第一段音频
        if sysfilename and text:
            processed_text = format_phone_number(text)
            audio_data = synthesize_audio(processed_text, voice_path=VOICE_PATH, speed=speed_callable, max_length=100)

            if audio_data is None:
                log.info("分段合成未生成音频，跳过第一段音频生成")
            else:
                raw_path = os.path.join(output_dir, sysfilename)
                sf.write(raw_path, audio_data, 24000)
                log.info(f"24K合成完成，保存路径: {raw_path}")

                # 转换为 8k 16bit mono 用来电话放音
                audio = AudioSegment.from_wav(raw_path)
                audio = audio.set_frame_rate(8000).set_sample_width(2).set_channels(1)
                
                audio = audio[:-750]
                audio.export(raw_path, format='wav')
                log.info(f"转换格式完成:{sysfilename} （8kHz, 16bit, mono）")
                log.info(f"合成完成:{sysfilename}")
        else:
            log.info("sysfilename或text为空，跳过第一段音频生成")
        # 如果TELE_CODE不为空，并且是转接消息。生成额外的被叫接通提示音频
        switch_val = str(data.get("SWITCH", "0")).strip()
        if TELE_CODE and switch_val == "1":
            try:
                if RESULT_NAME and RESULT_JOB:
                    greeting = f"你好，{RESULT_NAME}{RESULT_JOB}"
                else:
                    greeting = "你好"
                
                # 然后处理来电方信息
                if CALL_UNIT or CALL_NAME:
                    caller_info = f"这边是{CALL_UNIT}{CALL_NAME}{CALL_JOB}找您"
                elif CALLER:
                    caller_info = f"这边是{CALLER}找您"
                else:
                    caller_info = "有人找您"
                
                # 组合完整提示语
                prompt_text = f"{greeting}，{caller_info}。。三秒后将为您自动接通。。如不便接听。。请挂机。 。"
                
                log.info(f"生成接通提示音频，内容: {prompt_text}")
                
                processed_prompt = format_phone_number(prompt_text)
                prompt_audio_data = synthesize_audio(processed_prompt, voice_path=VOICE_PATH, speed=speed_callable, max_length=100)
                if prompt_audio_data is None:
                    raise Exception("分段合成未生成提示音频")
                
                # 生成提示音频文件名 - 使用时间戳作为文件名
                timestamp = int(time.time() * 1000) 
                prompt_filename = f"prompt_{channelNumber_id}_{timestamp}.wav"
                prompt_path = os.path.join(output_dir, prompt_filename)

                sf.write(prompt_path, prompt_audio_data, 24000)
                prompt_audio = AudioSegment.from_wav(prompt_path)
                prompt_audio = prompt_audio.set_frame_rate(8000).set_sample_width(2).set_channels(1)
                prompt_audio = prompt_audio[:-750]
                prompt_audio.export(prompt_path, format='wav')
                
                log.info(f"接通提示音频合成完成: {prompt_filename}")
                
                prompt_file = prompt_filename
            except Exception as e:
                log.error(f"生成接通提示音频失败: {e}")
                prompt_file = ""
        
        TELE_CODE = TELE_CODE or ""
            
        # 如果跳过了第一段音频生成，FILE字段应该为空
        if not text or not sysfilename:
            sysfilename = ""
            
        # 确保prompt_file变量存在
        if 'prompt_file' not in locals():
            prompt_file = ""
            
        message = (
            f"AI114_TTS_RESULT:"
            f"CHANNEL={channelNumber_id}:"
            f"SEQ={requestID}:"
            f"FILE={sysfilename}:"
            f"PHONE={TELE_CODE}:"
            f"SWITCH={SWITCH}:"
            f"PROMPT_FILE={prompt_file}:"
        )
        mq.publish(message)
        log.info(f"TTS服务发送消息出去: {message}")
    except Exception as e:
        log.error(f"TTS服务错误: {e}")


# 服务状态变量
service_start_time = time.time()

@app.route('/tts/health', methods=['GET'])
def health_check():
    global service_start_time
    
    current_time = time.time()
    uptime = current_time - service_start_time if service_start_time else 0
    
    return jsonify({
        "status": "running",
        "uptime_seconds": int(uptime),
        "start_time": service_start_time,
        "current_time": current_time
    })

def http_server(threadName, delay):
    """HTTP服务器"""
    try:
        app.run('0.0.0.0', 8333)
    except:
        print("HTTP服务器启动失败")
if __name__ == '__main__':
    log.info("TTS 服务启动，准备监听队列 InteractionSend...")
    
    # 启动HTTP服务器线程
    http_thread = threading.Thread(target=http_server, args=("HTTP服务器", 0))
    http_thread.daemon = True
    http_thread.start()
    log.info("HTTP服务器已启动，端口: 8333")
    
    mq = RabbitMQ()
    mq.consume(callback=handle_message)
