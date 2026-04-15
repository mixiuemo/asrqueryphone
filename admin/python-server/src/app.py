
import sys
import os
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from routes.user import user_bp  # 引入用户路由蓝图
from routes.role import role_bp
from routes.keywords import keywords_bp, set_MQ
from routes.serviceStatus import server_set_bp
from routes.trainConfig import train_config_bp
from routes.paraConfig import config_bp, set_MQ as set_config_MQ
from routes.tele import tele_bp
from routes.auth import auth_bp
from routes.upload.upload import upload_bp
from routes.logs import result_bp
from routes.welconfig import wel_config_bp
from routes.voicePrintLog import voiceprint_bp
from routes.connectMysql import get_db_connection
from routes.asrttstool import asrttstool_bp
from routes.mqtest import mqtest_bp, set_MQ as set_mqtest_MQ, start_mqtest_listener

import configparser
import os
import sys
import threading
import json

sys.path.append('../../../common')
from rabbitmq import RabbitMQ

MQ = RabbitMQ()
MQ.connect()

MQ_publisher = RabbitMQ()
MQ_publisher.connect()

set_MQ(MQ_publisher)
set_config_MQ(MQ_publisher)
set_mqtest_MQ(MQ_publisher)

# 定义MQ消息处理函数
def process_message(ch, method, properties, body):
    try:
        message = body.decode('utf-8')
        ignored_prefixes = [
            "HEARTBEAT:ASR", "HEARTBEAT:VOICECARD", "INTE_MSG","ASR_MSG",
            "RECORD", "AI114_TTS_RESULT", "HOTWORD","UpdateAi114Config",
            "HANGUP","HEARTBEAT:INBOUNDCALL",
            "HEARTBEAT:PLATFORMSERVER","语音卡录音程序"
        ]
        
        if any(message.startswith(prefix) for prefix in ignored_prefixes):
            return

        # Ignore specific JSON messages by type
        try:
            json_msg = json.loads(message)
            if isinstance(json_msg, dict) and json_msg.get("type") == "AISPEAKER-ASR-RESULT":
                return
        except Exception:
            pass
        print(f"收到MQ消息: {message}")
        
        if message == "VOICECARD_START" or message == "INTERACTION_START":
            conn = get_db_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT name, value FROM ai114_config WHERE name IN ('ai114_zrg', 'ai114_zj', 'ai114_unknown_policy')"
                    )
                    config_values = {row['name']: row['value'] for row in cursor.fetchall()}
                    
                    zrg_value = config_values.get('ai114_zrg', '0')
                    zj_value = config_values.get('ai114_zj', '0')
                    unk_value = config_values.get('ai114_unknown_policy', '0')
                    
                    # 发送更新配置消息
                    update_message = (
                        f"UpdateAi114Config:ai114_zrg={zrg_value}:ai114_zj={zj_value}"
                        f":ai114_unknown_policy={unk_value}"
                    )
                    MQ_publisher.publish(update_message)
                    print(f"发送配置更新消息: {update_message}")
            finally:
                if conn:
                    conn.close()
    except Exception as e:
        print(f"处理MQ消息时出错: {e}")

# 启动MQ消息监听
def start_mq_listener():
    try:
        mq_listener = RabbitMQ()
        mq_listener.connect()
        mq_listener.consume(process_message)  # 尝试使用consume方法
        print("MQ消息监听已启动")
    except Exception as e:
        print(f"启动MQ消息监听时出错: {e}")
        # 打印更详细的错误信息
        import traceback
        traceback.print_exc()

# 配置 CORS
BUILD_DIR = os.path.join(os.path.dirname(__file__), '../../web/build')
STATIC_DIR = os.path.join(BUILD_DIR, 'static')
app = Flask(__name__, static_folder=STATIC_DIR, static_url_path='/static')
CORS(app)  

def init_database():
    """初始化数据库，检查并创建基础表"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name = 'ai114_config'
            """)
            result = cursor.fetchone()
            
            if result['count'] == 0:
                cursor.execute("""
                    CREATE TABLE ai114_config (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        value VARCHAR(255) NOT NULL,
                        `desc` VARCHAR(500)
                    ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                """)
                print("ai114_config表创建成功")
                
                initial_configs = [
                    ('ai114_zrg', '0', '是否开启转人工功能'),
                    ('ai114_zj', '0', '是否开启转接功能'),
                    (
                        'ai114_unknown_policy',
                        '0',
                        '库外号码策略：0=仅查号不转接；1=查号且可转接(受转接总开关约束)；2=直转人工(受转人工总开关约束)',
                    ),
                ]
                
                for name, value, desc in initial_configs:
                    cursor.execute("""
                        INSERT INTO ai114_config (name, value, `desc`) 
                        VALUES (%s, %s, %s)
                    """, (name, value, desc))
                
                conn.commit()
                print("初始配置数据插入成功")
            else:
                print("ai114_config表已存在")

                try:
                    cursor.execute("""
                        ALTER TABLE ai114_config
                        CONVERT TO CHARACTER SET utf8mb4
                        COLLATE utf8mb4_unicode_ci
                    """)
                except Exception as alter_error:
                    print(f"ai114_config字符集转换失败: {alter_error}")
                
                cursor.execute(
                    "SELECT name FROM ai114_config WHERE name IN ('ai114_zj', 'ai114_zrg', 'ai114_unknown_policy')"
                )
                rows = cursor.fetchall()
                existing_fields = [row['name'] if isinstance(row, dict) else row[0] for row in rows]
                
                missing_fields = []
                if 'ai114_zj' not in existing_fields:
                    missing_fields.append(('ai114_zj', '0', '转人工开关'))
                if 'ai114_zrg' not in existing_fields:
                    missing_fields.append(('ai114_zrg', '0', '转接开关'))
                if 'ai114_unknown_policy' not in existing_fields:
                    missing_fields.append((
                        'ai114_unknown_policy',
                        '0',
                        '库外号码策略：0=仅查号不转接；1=查号且可转接；2=直转人工(均受全局转接/转人工开关约束)',
                    ))
                
                if missing_fields:
                    for name, value, desc in missing_fields:
                        cursor.execute("""
                            INSERT INTO ai114_config (name, value, `desc`) 
                            VALUES (%s, %s, %s)
                        """, (name, value, desc))
                        print(f"添加字段: {name} - {desc}")
                    
                    conn.commit()
                    print("缺失字段添加完成")
                else:
                    print("所有必要字段已存在，无需添加")

            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name = 'ai114_user'
            """)
            user_table = cursor.fetchone()

            if user_table['count'] == 0:
                cursor.execute("""
                    CREATE TABLE ai114_user (
                        id INT NOT NULL AUTO_INCREMENT,
                        username VARCHAR(50) NOT NULL,
                        password VARCHAR(100) NOT NULL,
                        employee_id VARCHAR(20) NOT NULL,
                        role VARCHAR(50) NOT NULL,
                        department VARCHAR(100) NOT NULL,
                        PRIMARY KEY (id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
                print("ai114_user表创建成功")

            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name = 'ai114_role'
            """)
            role_table = cursor.fetchone()
            if role_table['count'] == 0:
                cursor.execute("""
                    CREATE TABLE ai114_role (
                        id INT NOT NULL AUTO_INCREMENT,
                        role_code VARCHAR(50) NOT NULL,
                        role_name VARCHAR(100) NOT NULL,
                        menu_paths JSON NOT NULL,
                        PRIMARY KEY (id),
                        UNIQUE KEY uk_role_code (role_code)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
                conn.commit()
                print("ai114_role表创建成功")

            cursor.execute("SELECT COUNT(*) as count FROM ai114_role")
            role_count = cursor.fetchone()
            if role_count['count'] == 0:
                all_paths = json.dumps([
                    '/tele', '/paraConfig', '/keywords', '/serviceStatus',
                    '/users', '/mqtest', '/logs', '/trainConfig', '/welConfig',
                ], ensure_ascii=False)
                only_tele = json.dumps(['/tele'], ensure_ascii=False)
                cursor.execute("""
                    INSERT INTO ai114_role (role_code, role_name, menu_paths) VALUES
                    (%s, %s, %s), (%s, %s, %s)
                """, ('admin', '管理员', all_paths, 'user', '普通用户', only_tele))
                conn.commit()
                print("ai114_role 初始角色已插入")

            try:
                cursor.execute("""
                    UPDATE ai114_user SET role = 'admin'
                    WHERE role IN ('管理员', 'Admin', 'ADMIN')
                """)
                cursor.execute("""
                    UPDATE ai114_user SET role = 'user'
                    WHERE role IN ('普通用户', 'User', 'USER')
                """)
                conn.commit()
            except Exception as mig_e:
                print(f"ai114_user.role 历史值迁移: {mig_e}")

            cursor.execute("SELECT COUNT(*) as count FROM ai114_user")
            user_count = cursor.fetchone()
            if user_count['count'] == 0:
                cursor.execute("""
                    INSERT INTO ai114_user (username, password, employee_id, role, department)
                    VALUES (%s, %s, %s, %s, %s)
                """, ("admin", "admin", "admin", "admin", "admin"))
                conn.commit()
                print("ai114_user初始化admin用户完成")
                
    except Exception as e:
        print(f"数据库初始化失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'conn' in locals():
            conn.close()

init_database()

# 在单独的线程中启动MQ监听
threading.Thread(target=start_mq_listener, daemon=True).start()
start_mqtest_listener()

@app.route('/')
def index():
    return send_from_directory(BUILD_DIR, 'index.html')

# 处理前端路由，所有未匹配的路由都返回 index.html
@app.route('/<path:path>')
def catch_all(path):
    if path.startswith('api/'):
        return jsonify({'error': 'Not Found'}), 404
    file_path = os.path.join(BUILD_DIR, path)
    if os.path.isfile(file_path):
        return send_from_directory(BUILD_DIR, path)
    return send_from_directory(BUILD_DIR, 'index.html')

# 读取配置文件
config = configparser.ConfigParser()
config_path = os.path.join(os.path.dirname(__file__), '../../../../etc/config.ini')
config.read(config_path, encoding='utf-8')

# 注册蓝图
app.register_blueprint(user_bp, url_prefix='/api/users')
app.register_blueprint(role_bp, url_prefix='/api/roles')
app.register_blueprint(keywords_bp, url_prefix='/api/keywords')
app.register_blueprint(server_set_bp, url_prefix='/api/serviceStatusRoutes')
app.register_blueprint(train_config_bp, url_prefix='/api/trainConfig')
app.register_blueprint(config_bp, url_prefix='/api/paraConfig')
app.register_blueprint(tele_bp, url_prefix='/api/tele')
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(upload_bp, url_prefix='/api/upload')
# app.register_blueprint(voice_bp, url_prefix='/api/embedding')
app.register_blueprint(result_bp, url_prefix='/api/auto114result')
app.register_blueprint(wel_config_bp, url_prefix='/api/welConfig')
app.register_blueprint(voiceprint_bp, url_prefix='/api/voicePrint')
app.register_blueprint(asrttstool_bp, url_prefix='/api/asrttstool')
app.register_blueprint(mqtest_bp, url_prefix='/api/mqtest')




# 读取配置文件
config_path = os.path.join(os.path.dirname(__file__), '../../../../etc/config.ini')  # 配置文件路径
print('configPath', config_path)

config = configparser.ConfigParser()
if os.path.exists(config_path):
    config.read(config_path, encoding='utf-8')
    print('Config loaded successfully:', config_path)
else:
    print('Config file not found:', config_path)
    # 提供默认配置以便继续运行
    config['VOICEPRINT'] = {'VP_SERVER_MEDIA_PATH': '/path/to/voiceprint/media'}
    config['MEDIA'] = {
        'RECORD_WAV_ROOT': '/path/to/record/wav',
        'TTS_WAV_ROOT': '/path/to/tts/wav'
    }

# 挂载静态文件服务
@app.route('/uploads/<path:filename>')
def serve_uploads(filename):
    uploads_dir = os.path.join(os.path.dirname(__file__), '../uploads')
    return send_from_directory(uploads_dir, filename)

@app.route('/vad/<path:filename>')
def serve_vad(filename):
    vad_dir = os.path.join(os.path.dirname(__file__), '../vad')
    return send_from_directory(vad_dir, filename)

@app.route('/media/<path:filename>')
def serve_media(filename):
    media_path = config['VOICEPRINT']['VP_SERVER_MEDIA_PATH']
    return send_from_directory(media_path, filename)

@app.route('/record/<path:filename>')
def serve_record(filename):
    record_path = config['MEDIA']['RECORD_WAV_ROOT']
    return send_from_directory(record_path, filename)

@app.route('/tts/<path:filename>')
def serve_tts(filename):
    tts_path = config['MEDIA']['TTS_WAV_ROOT']
    return send_from_directory(tts_path, filename)



# 启动服务器
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
