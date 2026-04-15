from flask import Blueprint, jsonify, request
from .connectMysql import get_db_connection
from pydub import AudioSegment
import os
import requests
from werkzeug.utils import secure_filename


# 创建蓝图
asrttstool_bp = Blueprint('asrttstool', __name__)

UPLOAD_FOLDER = "D:/AI114/media/record/asrtts/"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # 如果文件夹不存在，则创建它

# 指定允许上传的文件类型
ALLOWED_EXTENSIONS = {'wav', 'mp3', 'ogg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 上传
@asrttstool_bp.route('/voicefile', methods=['POST'])
def upload_voice_file():
    try:
        if "file" not in request.files:
            return jsonify({"error": "未找到上传的文件"}), 400

        file = request.files["file"]

        if file.filename == "":
            return jsonify({"error": "未选择文件"}), 400

        if file and allowed_file(file.filename):
            original_filename = secure_filename(file.filename)
            file_path = os.path.join(UPLOAD_FOLDER, original_filename)
            file.save(file_path)

            # 转换音频格式：16000Hz, 单声道
            audio = AudioSegment.from_file(file_path)
            converted_audio = audio.set_frame_rate(16000).set_channels(1)

            # 生成新的文件名（替换扩展名为 .wav）
            base_name, _ = os.path.splitext(original_filename)
            new_filename = f"{base_name}.wav"
            converted_file_path = os.path.join(UPLOAD_FOLDER, new_filename)
            converted_audio.export(converted_file_path, format="wav")
            print("converted_file_path",converted_file_path)
            # 删除原始文件（可选）
            # os.remove(file_path)
            print("new_filename",new_filename)

            # 发起 HTTP 请求
            target_url = "http://192.168.40.245:8114/process_audio"  # 替换为你需要请求的目标URL
            payload = {"msg": f"RECORD:CHANNEL=1:SEQ=0:FILE=asrtts/{new_filename}:PHONE=15173042592"}
            response = requests.post(target_url, json=payload)

            return jsonify({
                "message": "文件处理完成并已发送至目标服务",
                "response_status_code": response.status_code,
                "response_text": response.text,
                "converted_file": new_filename
            }), 200

        else:
            return jsonify({"error": "不允许的文件类型"}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500
