from flask import Blueprint, jsonify, request
import configparser
import pandas as pd
import os
import json
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor
import aiohttp
from routes.connectMysql import get_db_connection
from flask import send_file
import requests
from pydub import AudioSegment
import threading
import time

# 创建蓝图
voice_bp = Blueprint('voice', __name__)

# 文件上传配置
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# 配置文件路径
config_path = os.path.join(os.path.dirname(__file__), '../../../../../../../etc/config.ini')

# 读取配置文件
config = configparser.ConfigParser()
if os.path.exists(config_path):
    config.read(config_path, encoding='utf-8')
    print(f"Config loaded successfully: {config_path}")
else:
    print(f"Config file not found: {config_path}")
    # 提供默认配置以便继续运行
    config = {
        'VOICEPRINT': {
            'VP_SERVER_URL': 'http://default-url.com'  # 替换为默认值
        },
        'AI_modal': {
            'ip': '127.0.0.1',
            'port': 5001
        },
        'TTS': {
            'ip': '127.0.0.1',
            'port': 5001
        }
    }

# 从配置中获取声纹服务 URL
# voiceprint_url = config['VOICEPRINT']['VP_SERVER_URL'].replace('identify', 'voiceprantchange') if isinstance(config, configparser.ConfigParser) else config['VOICEPRINT']['VP_SERVER_URL'].replace('identify', 'voiceprantchange')
# print(f"Voiceprint URL: {voiceprint_url}")
voiceprint_url = config['VOICEPRINT']['VP_SERVER_URL'] + "voiceprantchange"
print(f"Voiceprint URL: {voiceprint_url}")

# voiceidentify_url = config['VOICEPRINT']['VP_SERVER_URL'] + "identify"
voiceidentify_url = config['VOICEPRINT']['VP_SERVER_URL'] + "testidentify"
save_dir = config['VOICEPRINT']['VP_SERVER_MEDIA_PATH']

# 工具函数：向量相似度计算
def parse_vec(str_vec):
    return list(map(float, str_vec.replace('[', '').replace(']', '').split(',')))

def dot_product(v1, v2):
    return sum(a * b for a, b in zip(v1, v2))

def magnitude(v):
    return (sum(a * a for a in v)) ** 0.5

def cosine_similarity(v1, v2):
    mag1 = magnitude(v1)
    mag2 = magnitude(v2)
    if mag1 == 0 or mag2 == 0:
        return 0
    return dot_product(v1, v2) / (mag1 * mag2)

# 文件处理逻辑
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'xls', 'xlsx'}

# 文件清理逻辑
def clean_up_file(file_path):
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        print(f"File cleanup failed: {e}")

def convert_audio(input_file, output_file, file_type):
    print(f"convert_audio: 输入文件:", input_file, " 输出文件:", output_file, " 文件类型:", file_type)
    try:
        # # 加载音频文件
        # audio = AudioSegment.from_file(input_file, format=file_type)
        # # 将音频转换为单声道
        # audio = audio.set_channels(1)
        # # 将音频转换为16k采样率
        # audio = audio.set_frame_rate(16000)
        # # 保存转换后的音频文件
        # audio.export(output_file, format="wav")
        # return len(audio) / 1000

        ffmpegCmd = f"..\\..\\scripts\\pcm16.bat {input_file} {output_file} " 
        os.system(ffmpegCmd)
        audio = AudioSegment.from_file(output_file)
        return len(audio) / 1000
    except Exception as e:
        print(f"1111111111111111111111111: {e}")
        return 0

def convert_audio_form_mp3(input_file, output_file):
    # 加载音频文件
    audio = AudioSegment.from_mp3(input_file)
    # 将音频转换为单声道
    audio = audio.set_channels(1)
    # 将音频转换为16k采样率
    audio = audio.set_frame_rate(16000)
    # 保存转换后的音频文件
    audio.export(output_file, format="wav")

# 需要执行的任务
# 通知声纹服务更新
def my_task():
    try:
        response = requests.get(voiceprint_url)
        if response.status_code != 200:
            print(f"Failed to notify voiceprint service: {response.status_code}")
    except Exception as e:
        print(f"Error notifying voiceprint service: {str(e)}")
    

# 查询声纹列表
@voice_bp.route('/', methods=['GET'])
def get_speaker_embeddings():
    try:
        search_keyword = request.args.get('search', '')
        query = 'SELECT * FROM ai114_speaker_embeddings'
        params = []

        if search_keyword:
            query += ' WHERE speakerName LIKE %s OR uploadName LIKE %s'
            params.extend([f'%{search_keyword}%', f'%{search_keyword}%'])

        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()
        return jsonify(rows)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# 添加新的用户记录
@voice_bp.route('/add', methods=['POST'])
def add_speaker_embedding():
    try:
        data = request.get_json()
        speaker_name = data.get('speakerName')
        file_name = data.get('fileName')
        embedding = data.get('embedding')
        upload_name = data.get('uploadName')
        user_type = data.get('userType')
        print("1111111111111111111111Voiceprint", user_type)

        if not all([speaker_name, file_name, embedding]):
            return jsonify({'error': 'Missing required parameters'}), 400

        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        createTime = datetime.now().timestamp()
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute('''
                INSERT INTO ai114_speaker_embeddings (speakerName, fileName, embedding, userType, uploadName, currentTime, `createTime` , `createdAt`) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                '''
                ,
                (speaker_name, file_name, embedding, user_type, upload_name, current_time, int(createTime), current_time)
            )
            conn.commit()
            insert_id = cursor.lastrowid
        print(f"1111111111111111111111Voiceprint URL: {voiceprint_url}")

        # 通知声纹服务更新
        thread = threading.Thread(target=my_task)
        thread.start()  # 启动线程

        return jsonify({'id': insert_id}), 201
    except Exception as e:
        print(f"Error Exception: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# 更新用户记录
@voice_bp.route('/<int:id>', methods=['PUT'])
def update_speaker_embedding(id):
    try:
        data = request.get_json()
        updatable_fields = ['speakerName', 'fileName', 'embedding', 'uploadName', 'currentTime']
        updates = []
        values = []
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        data['currentTime'] = current_time
        for field in updatable_fields:
            if field in data and data[field] is not None:
                updates.append(f"{field} = %s")
                values.append(data[field])
        if not updates:
            return jsonify({'error': 'No updatable fields provided'}), 400

        values.append(id)
        conn = get_db_connection()
        with conn.cursor() as cursor:
            print(f"UPDATE ai114_speaker_embeddings SET {', '.join(updates)} WHERE id = %s")
            print(f"11111111111111",values)
            cursor.execute(
                f"UPDATE ai114_speaker_embeddings SET {', '.join(updates)} WHERE id = %s",
                values
            )
            conn.commit()
        print(f"22222222222222222222222Voiceprint URL: {voiceprint_url}")

        # 通知声纹服务更新
        thread = threading.Thread(target=my_task)
        thread.start()  # 启动线程

        return jsonify({
            'success': True,
            'message': 'Update successful',
            'updatedFields': updates
        })
    except Exception as e:
        print(f"Error 222222222222222222222222 333333333333333 service: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# 删除用户记录
@voice_bp.route('/<int:id>', methods=['DELETE'])
def delete_speaker_embedding(id):
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # 检查记录是否存在
            cursor.execute('SELECT id FROM ai114_speaker_embeddings WHERE id = %s', (id,))
            existing = cursor.fetchone()
            if not existing:
                return jsonify({'error': 'Record not found'}), 404

            # 删除记录
            cursor.execute('DELETE FROM ai114_speaker_embeddings WHERE id = %s', (id,))
            conn.commit()
            print(f"33333333333333333333333Voiceprint URL: {voiceprint_url}")
            thread = threading.Thread(target=my_task)
            thread.start()  # 启动线程

        return jsonify({
            'success': True,
            'message': 'Record permanently deleted',
            'deletedEmployeeId': id
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# 声纹识别接口
@voice_bp.route('/identify', methods=['POST'])
def identify_speaker():
    try:
        current_vector = request.json.get('currentVector')
        if not current_vector:
            return jsonify({'error': 'Missing currentVector'}), 400

        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute('SELECT speakerName, embedding FROM ai114_speaker_embeddings')
            rows = cursor.fetchall()

        max_similarity = 0
        identified_name = '该用户未注册'

        for row in rows:
            vec = parse_vec(row['embedding'])
            similarity = cosine_similarity(vec, current_vector)

            if similarity > max_similarity:
                max_similarity = similarity
                identified_name = row['speakerName']

        if max_similarity > 0.4:
            return jsonify({ 'ret': 200, 'result': f'识别成功,当前声音为：{identified_name}' })
        else:
            return jsonify({ 'ret': 200, 'result': '识别失败,当前声音未注册！' })
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# 语音转文字接口
@voice_bp.route('/generateAudioToTxt', methods=['POST'])
def generate_audio_to_txt():
    try:
        data = request.json.get('data')
        if not data:
            return jsonify({'error': 'Missing audio data'}), 400

        response = requests.post(
            f"{global_config.ARS['ip']}:{global_config.ARS['port']}/process_audio",
            json={'data': data},
            headers={'Content-Type': 'application/json'}
        )

        if response.status_code != 200:
            return jsonify({'result': 'ERR_QUERY', 'ret': 'Audio processing failed'}), 500

        return jsonify({
            'ret': response.json(),
            'result': 200
        })
    except Exception as e:
        return jsonify({'result': 'ERR_QUERY', 'ret': str(e)}), 500

# 查询AI大模型接口
@voice_bp.route('/queryAIModal', methods=['POST'])
def query_ai_modal():
    try:
        data = request.get_json()
        query_text = data.get('query_text')

        ai_modal_config = config['AI_modal'] if isinstance(config, configparser.ConfigParser) else config['AI_modal']
        ip = ai_modal_config.get('ip', '127.0.0.1')
        port = ai_modal_config.get('port', 5001)

        response = requests.post(
            f"http://{ip}:{port}/talk",
            json={'data': query_text},
            headers={'Content-Type': 'application/json'}
        )

        if response.status_code != 200:
            return jsonify({'result': 'ERR_QUERY', 'ret': 'AI modal query failed'}), 500

        return jsonify({
            'ret': response.json(),
            'result': 200
        })
    except Exception as e:
        return jsonify({'result': 'ERR_QUERY', 'ret': str(e)}), 500

# 合成音频接口
@voice_bp.route('/generateAudio', methods=['POST'])
def generate_audio():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'result': 'ERR_QUERY', 'ret': 'Missing audio data'}), 400

        response = requests.post(
            f"{global_config.TTS['ip']}:{global_config.TTS['port']}/txtToAudio",
            json={'data': data},
            headers={'Content-Type': 'application/json'}
        )

        if response.status_code != 200:
            return jsonify({'result': 'ERR_QUERY', 'ret': 'Audio generation failed'}), 500

        return jsonify(response.json())
    except Exception as e:
        return jsonify({'result': 'ERR_QUERY', 'ret': str(e)}), 500
@voice_bp.route('/template', methods=['GET'])
def download_template():
    try:
        # 创建模板数据
        template_data = {
            '序号': [1],
            '用户名': ['张三'],
            '人员类型(1:普通用户,2:话务员)': [1],
            '文件路径': ['D:/AI114/media/record/张三.wav'],
        }

        # 创建 DataFrame
        df = pd.DataFrame(template_data)

        # 指定文件保存的绝对路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(current_dir, 'embedding_template.xlsx')

        # 确保目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # 保存为 Excel 文件
        df.to_excel(output_path, index=False, engine='openpyxl')

        # 发送文件
        return send_file(output_path, as_attachment=True, download_name='embedding_template.xlsx')

    except Exception as e:
        print(f"Error generating template: {e}")
        return jsonify({'status': 'error', 'message': '模板生成失败'}), 500

# 导入声音文件
@voice_bp.route('/importvoice', methods=['POST'])
def import_audio():
    required_columns = ['序号', '用户名', '人员类型(1:普通用户,2:话务员)', '文件路径']
    file = request.files.get('file')
    if not file or not allowed_file(file.filename):
        return jsonify({'status': 'error', 'message': '未收到文件或文件类型不支持'}), 400

    try:
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)

        # 读取 Excel 文件
        df = pd.read_excel(file_path)
        
        # 检查所需列是否存在
        if not all(column in df.columns for column in required_columns):
            return jsonify({'status': 'error', 'message': 'Excel文件缺少必要的列'}), 400
        
        # 处理文件路径，提取文件名
        df['fileName'] = df['文件路径'].apply(lambda x: os.path.basename(x) if pd.notna(x) else None)

        # 检查文件路径中是否存在文件名
        if df['fileName'].isnull().any():
            return jsonify({'status': 'error', 'message': '文件路径中存在空值或无效路径'}), 400

        # 获取数据库连接
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                conn.begin()
                for _, row in df.iterrows():
                    speaker_name = row['用户名']
                    file_path2 = row['文件路径']
                    file_name = row['fileName']
                    user_type = row['人员类型(1:普通用户,2:话务员)']
                    embedding = ''  # 如果你有音频嵌入的相关处理可以在此插入
                    output_file = ''
                    # 通知声纹服务更新
                    try:
                        input_file = str(file_path2)
                        output_file = save_dir + file_name + "_out.wav"
                        print("input_file : ", input_file)
                        print("output_file : ", output_file)
                        file_type = os.path.splitext(input_file)[1].lstrip('.').lower()
                        convert_audio(file_path2, output_file, file_type)
                        params = {
                            'file_path': input_file,
                            "file_type": 1
                        }
                        #{file_path: "D:\AI114\media\voiceprint\fangkongjingbao-1.mp3"}
                        req_url = voiceidentify_url
                        response = requests.post(req_url, json=params)
                        # 检查是否成功响应
                        response.raise_for_status()

                        if response.status_code != 200:
                            print(f"Failed to notify voiceprint service: {response.status_code}")

                        response_json = response.json()
                        # print(f"Response JSON: {response_json}")
                        embedding = str(response_json['embedding'])
                    except Exception as e:
                        print(f"Error notifying voiceprint service: {str(e)}")
                    
                    #* 插入数据库 
                    # ALTER TABLE `rgt`.`ai114_speaker_embeddings` ADD COLUMN `userType` INT(11) DEFAULT 1 NULL COMMENT '人员类型(1:普通用户,2:话务员)' AFTER `embedding`; 
                    #ALTER TABLE `rgt`.`ai114_speaker_embeddings` ADD COLUMN `current_time` VARCHAR(255) NULL AFTER `uploadName`, ADD COLUMN `createTime` DOUBLE NULL AFTER `current_time`, ADD COLUMN `createdAt` VARCHAR(50) NULL AFTER `createTime`; 
                    # 
                    # */
                    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    createTime = datetime.now().timestamp()
                    #插入数据
                    sql = '''
                        INSERT INTO ai114_speaker_embeddings (speakerName, fileName, embedding, userType, uploadName, currentTime, `createTime` , `createdAt`) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    '''
                    #假设 embedding 是一些预处理的音频数据，可以在这里放置实际的嵌入数据，暂时使用空字符串作为占位
                    print("SQL:", sql)
                    print("Parameters:", (speaker_name, file_name, embedding, user_type, output_file, current_time, int(createTime), current_time))
                    #执行插入语句
                    # cursor.execute(sql, (speaker_name, file_name, embedding, user_type, output_file, current_time, int(createTime), current_time))
                conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Error: {e}")
            return jsonify({'status': 'error', 'message': f'数据库写入失败: {e}'}), 500
        finally:
            conn.close()

        clean_up_file(file_path)  # 清理临时上传的文件
        thread = threading.Thread(target=my_task)
        thread.start()  # 启动线程
        print("主线程继续执行")

        return jsonify({
            'status': 'success',
            'message': '导入成功',
            'imported': len(df),
            'sample': df.head(3).to_dict(orient='records')
        })

    except Exception as e:
        print(f"Error: {e}")
        clean_up_file(file_path)
        return jsonify({'status': 'error', 'message': str(e)}), 500
