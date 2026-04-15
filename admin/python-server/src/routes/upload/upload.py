from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename
import os
import pymysql
import shutil
from datetime import datetime
from routes.connectMysql import get_db_connection

# 创建蓝图
upload_bp = Blueprint('upload', __name__)

# 读取配置文件
def read_config(config_path):
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_content = f.read()
        config = {}
        current_section = None
        for line in config_content.split('\n'):
            line = line.strip()
            if not line or line.startswith(';'):
                continue
            if line.startswith('[') and line.endswith(']'):
                current_section = line[1:-1]
                config[current_section] = {}
            elif current_section and '=' in line:
                key, value = line.split('=', 1)
                config[current_section][key.strip()] = value.strip()
        return config
    except Exception as e:
        print(f"Error reading config file: {e}")
        return {
            'VOICEPRINT': {
                'VP_SERVER_MEDIA_PATH': os.path.join(os.path.dirname(__file__), '../../../uploads')
            }
        }

config_path = os.path.join(os.path.dirname(__file__), '../../../../../../etc/config.ini')
config = read_config(config_path)

# 文件上传路由
@upload_bp.route('/upload', methods=['POST'])
def upload_file():
    print('哈哈哈111', 111)
    upload_dir = config.get('VOICEPRINT', {}).get('VP_SERVER_MEDIA_PATH')
    if not upload_dir:
        upload_dir = os.path.join(os.path.dirname(__file__), '../../../uploads')
    
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir, exist_ok=True)

    file = request.files.get('file')
    if not file:
        return jsonify({'status': 'error', 'message': '未收到文件'}), 400

    try:
        filename = secure_filename(file.filename)
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)

        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                sql = '''
                    INSERT INTO ai114_files 
                    (original_name, file_path, mime_type, file_size, upload_time) 
                    VALUES (%s, %s, %s, %s, NOW())
                '''
                cursor.execute(sql, (
                    filename,
                    file_path,
                    file.mimetype,
                    file.content_length
                ))
                conn.commit()
                insert_id = cursor.lastrowid
            return jsonify({
                'status': 'success',
                'file_id': insert_id,
                'original_name': filename,
                'file_path': file_path,
                'mime_type': file.mimetype,
                'file_size': file.content_length,
                'upload_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        except Exception as e:
            conn.rollback()
            return jsonify({'status': 'error', 'message': '数据库写入失败', 'details': str(e)}), 500
        finally:
            conn.close()

    except Exception as e:
        return jsonify({'status': 'error', 'message': '文件上传失败', 'details': str(e)}), 500