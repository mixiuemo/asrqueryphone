from flask import Flask, request, jsonify
import os
import re
import _thread
import json
import time
import subprocess
import sys
import base64
# 1. 彻底禁用 tqdm 进度条
os.environ["TQDM_DISABLE"] = "1"
# 2. 禁用 HuggingFace 相关的进度条
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
from funasr import AutoModel
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import sys
sys.path.append('../../common')
from sys_config import SysConfig
from rabbitmq import RabbitMQ
from loguru import logger
import builtins

# Flask应用
app = Flask(__name__)
# 配置
QUEUE_NAME = 'AI114'
ENABLE_HTTP = os.getenv("ENABLE_HTTP", "0") == "1"
HTTP_PORT = int(os.getenv("HTTP_PORT", "8111"))
WORKER_NAME = os.getenv("WORKER_NAME", f"asr-worker-{os.getpid()}")
# 仅当前ASR进程启用共享队列模式，避免影响其它服务
os.environ.setdefault("MQ_CONSUME_MODE", "shared")
os.environ.setdefault("ASR_CONSUME_QUEUE", "asr_shared_queue_runmain")
os.environ.setdefault("MQ_PREFETCH", "1")

def _print(*args, **kwargs):
    builtins.print(f"[{WORKER_NAME}]", *args, **kwargs, flush=True)

print = _print

Config = SysConfig()
MQ = RabbitMQ()
MQ.connect()
MQ_publisher = RabbitMQ()

# 全局变量
model = None
hotword_string = ""
DEFAULT_HOTWORDS = [
    "转人工",
    "人工客服",
    "转人工客服",
    "人工服务",
    "转客服",
    "人工坐席",
    "转人工坐席",
    "人工服务台",
    "转人工服务",
    "请转人工",
    "我要人工",
    "需要人工",
    "人工帮助",
    "转接人工",
    "转接客服",
    "客服人工",
    "人工接听",
    "转人工台",
    "人工处理",
    "转人工热线",
    "请求人工",
    "呼叫人工",
    "找人工",
    "找客服",
    "转人工专席",
	"转接",
]

RETRY_BAD_RESULTS = {"the"}

def _normalize_text(text):
    return (text or "").strip().replace(" ", "").lower()

def _is_bad_result(text):
    normalized = _normalize_text(text)
    if not normalized:
        return True
    if normalized in RETRY_BAD_RESULTS:
        return True
    # 连续重复（例如“没有没有没有”）
    if re.fullmatch(r"(没有){2,}", normalized):
        return True
    return False

def _normalize_hotwords(lines):
    seen = set()
    result = []
    for raw in lines:
        word = (raw or "").strip()
        if not word:
            continue
        if word in seen:
            continue
        seen.add(word)
        result.append(word)
    return result

def load_model():
    """初始化语音识别模型"""
    global model 
    model = AutoModel(
        model="./iic/speech_paraformer-large-contextual_asr_nat-zh-cn-16k-common-vocab8404",
        model_revision="v2.0.4",
        device="cuda"
    )
    print("语音识别模型加载完成")

def load_hotwords():
    """从hotwords.txt加载热词"""
    global hotword_string
    try:
        hotwords = []
        if os.path.exists("hotwords.txt"):
            with open('hotwords.txt', 'r', encoding='utf-8') as f:
                hotwords = f.read().splitlines()

        base_list = _normalize_hotwords(hotwords)
        merged_list = _normalize_hotwords(base_list + DEFAULT_HOTWORDS)

        if len(merged_list) > len(base_list):
            missing = [w for w in merged_list if w not in base_list]
            with open('hotwords.txt', 'a', encoding='utf-8') as f:
                for w in missing:
                    f.write(w + "\n")
            print(f"默认热词已追加到文件，共新增{len(missing)}个")

        hotword_string = ' '.join(merged_list)
        print(f"热词加载完成，共{len(merged_list)}个热词")
    except Exception as e:
        print(f"加载热词失败: {e}")
        hotword_string = ""

def find_audio_file_in_subdirs(root_dir, filename):
    """在子目录中递归搜索音频文件"""
    try:
        for root, dirs, files in os.walk(root_dir):
            if filename in files:
                found_path = os.path.join(root, filename)
                print(f"在子目录中找到文件: {found_path}")
                return found_path
        return None
    except Exception as e:
        print(f"搜索文件时出错: {e}")
        return None

def process_audio_file(audio_file_path):
    """处理音频文件，返回识别结果"""
    try:
        # 语音识别
        res = model.generate(
            input=audio_file_path, 
            language="zh", 
            batch_size_s=10, 
            hotword=hotword_string
        )
        
        if isinstance(res, list) and len(res) > 0 and 'text' in res[0]:
            identify_result = res[0]['text'].replace(" ", "")
        else:
            identify_result = "未找到文本字段"
        
        # 清理识别结果
        identify_result = re.sub(r'<\|\w+\|>', '', identify_result).strip()
        return identify_result
        
    except Exception as e:
        logger.error(f"语音识别失败: {e}")
        return None

def process_audio_bytes(audio_bytes):
    """处理PCM字节数据，返回识别结果"""
    try:
        if not audio_bytes:
            logger.error("音频数据为空")
            return None

        logger.info(f"开始识别PCM数据，大小: {len(audio_bytes)} 字节")
        res = model.generate(
            input=audio_bytes,
            language="zh",
            batch_size_s=10,
            hotword=hotword_string
        )

        if isinstance(res, list) and len(res) > 0 and 'text' in res[0]:
            identify_result = res[0]['text'].replace(" ", "")
        else:
            identify_result = "未找到文本字段"

        identify_result = re.sub(r'<\|\w+\|>', '', identify_result).strip()
        return identify_result

    except Exception as e:
        logger.error(f"PCM数据识别失败: {e}")
        return None

def is_likely_filename(value):
    if not value:
        return False
    if len(value) > 260:
        return False
    lower = value.lower()
    if '/' in value or '\\' in value:
        return True
    exts = ('.wav', '.mp3', '.m4a', '.aac', '.flac', '.ogg', '.pcm')
    return lower.endswith(exts)

def strip_data_url_prefix(b64_text):
    if not b64_text:
        return b64_text
    if ',' in b64_text and b64_text.strip().lower().startswith('data:'):
        return b64_text.split(',', 1)[1]
    return b64_text

def linseterVoiceCard(ch, method, properties, body):
    """处理MQ消息"""
    msg = body.decode('utf-8')
    ignored_prefixes = [
            "HEARTBEAT:ASR", "HEARTBEAT:VOICECARD", "INTE_MSG",
            "AI114_TTS_RESULT", "HOTWORD","VOICECARD_START","INTERACTION_START",
            "HEARTBEAT:PLATFORMSERVER","语音卡录音程序","ASR_MSG","INTE_MSG"
    ]
    
    if any(msg.startswith(prefix) for prefix in ignored_prefixes):
        return
    if "HOTWORD" in msg:
        load_hotwords()
        return
    elif "HANGUP:CHANNEL" in msg:
        print("用户挂机...")
        return
    elif "RECORD:CHANNEL" in msg:
        # 解析消息参数
        pattern = r"([^:=]+)(?:=([^:]*))?"
        matches = re.findall(pattern, msg)
        msg_dict = {match[0]: match[1] if match[1] else None for match in matches}
        
        channel = msg_dict['CHANNEL']
        seq = msg_dict['SEQ']
        phone = msg_dict['PHONE']
        userCircuit = msg_dict['USERCIRCUIT']
        file_or_data = msg_dict.get('FILE')
        print(f"收到语音卡消息{msg}")
        if not file_or_data:
            logger.debug("RECORD消息中缺少FILE字段")
            print("RECORD消息中缺少FILE字段")
            return

        identify_result = None
        is_pcm_data = False
        if is_likely_filename(file_or_data):
            mediaDir = Config.get('MEDIA','RECORD_WAV_ROOT')
            audio_file_path = os.path.join(mediaDir, file_or_data)
            
            if not os.path.exists(audio_file_path):
                audio_file_path = find_audio_file_in_subdirs(mediaDir, file_or_data)
                if not audio_file_path:
                    logger.debug(f"文件 {file_or_data} 在 {mediaDir} 及其子目录中未找到")
                    print(f"错误：文件 {file_or_data} 在 {mediaDir} 及其子目录中未找到")
                    return
            
            # 语音识别（文件）
            identify_result = process_audio_file(audio_file_path)
            if _is_bad_result(identify_result):
                print("识别结果疑似异常，尝试重试一次...")
                identify_result = process_audio_file(audio_file_path)
        else:
            # 语音识别（Base64音频数据）
            is_pcm_data = True
            audio_b64 = strip_data_url_prefix(file_or_data)
            logger.info(f"收到ASR PCM数据请求，数据长度: {len(audio_b64)}")
            print(f"收到ASR PCM数据请求，数据长度: {len(audio_b64)}")
            try:
                audio_bytes = base64.b64decode(audio_b64)
            except Exception as e:
                logger.error(f"Base64解码失败: {e}")
                return
            identify_result = process_audio_bytes(audio_bytes)
            if _is_bad_result(identify_result):
                print("识别结果疑似异常，尝试重试一次...")
                identify_result = process_audio_bytes(audio_bytes)
        if not identify_result:
            return
        
        print(f"识别结果: {identify_result}")
        
        # 构建发送消息
        msg = msg.replace('RECORD','ASR_MSG')
        sendMsg = msg + ":ASRCONTENT=" + identify_result + ":USERCIRCUIT=" + userCircuit + ":"
        
        # 发送到MQ
        MQ_publisher.publish(sendMsg.encode('utf-8'))
        if is_pcm_data:
            preview = file_or_data[:10] if file_or_data else ""
            log_msg = re.sub(r"FILE=[^:]*:", f"FILE=<PCM:{preview}...>:", sendMsg)
            print(f"发送消息: {log_msg}")
        else:
            print(f"发送消息: {sendMsg}")

class HotwordsFileHandler(FileSystemEventHandler):
    """热词文件变化处理器"""
    def on_modified(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith('hotwords.txt'):
            print("检测到热词文件变化，重新加载热词...")
            load_hotwords()
            print("热词热更新完成")

def start_hotwords_watcher():
    event_handler = HotwordsFileHandler()
    observer = Observer()
    observer.schedule(event_handler, path='.', recursive=False)
    observer.start()
    print("热词文件监控已启动")
    return observer

def http_server(threadName, delay):
    """HTTP服务器"""
    try:
        app.run('0.0.0.0', HTTP_PORT)
    except:
        print(f"HTTP服务器启动失败, port={HTTP_PORT}")

# 服务状态变量
service_start_time = None
@app.route('/asr/health', methods=['GET'])
def health_check():
    global service_start_time
    import time
    
    current_time = time.time()
    uptime = current_time - service_start_time if service_start_time else 0
    
    return jsonify({
        "status": "running",
        "worker_name": WORKER_NAME,
        "pid": os.getpid(),
        "uptime_seconds": int(uptime),
        "start_time": service_start_time,
        "current_time": current_time
    })

def execute():
    """主执行函数"""
    try:
        load_hotwords()
        MQ_publisher.consume(linseterVoiceCard)
    except Exception as e:
        print(f"执行异常: {str(e)}")
        execute()  # 重启

if __name__ == '__main__':
    print("启动语音识别服务...")
    print(f"worker={WORKER_NAME}, enable_http={ENABLE_HTTP}, http_port={HTTP_PORT}")
    service_start_time = time.time()
    load_model()
    # 启动热词文件监控
    observer = start_hotwords_watcher()
    # 启动HTTP服务器线程（仅主实例开启）
    if ENABLE_HTTP:
        _thread.start_new_thread(http_server, ("http-Thread", 1,))
    else:
        print("HTTP健康检查已禁用，当前实例仅消费MQ")
    try:
        execute()
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

