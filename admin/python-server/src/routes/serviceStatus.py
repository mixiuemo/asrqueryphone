from flask import Blueprint, jsonify, request
from .connectMysql import get_db_connection
import requests
import time

# 创建蓝图
server_set_bp = Blueprint('serviceStatus', __name__)
# 查询服务状态列表
@server_set_bp.route('/', methods=['GET'])
def get_server_sets():
    print('我吐了')
    search_keyword = request.args.get('search', '')
    query = 'SELECT * FROM ai114_serverSet'
    params = []

    if search_keyword:
        query += ' WHERE service LIKE %s'
        params.append(f'%{search_keyword}%')

    try:
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

# 添加新的服务状态记录
@server_set_bp.route('/', methods=['POST'])
def add_server_set():
    try:
        data = request.get_json()
        service = data.get('service')
        status = data.get('status')

        if not all([service, status]):
            return jsonify({'error': 'Missing required parameters'}), 400

        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = '''
                INSERT INTO ai114_serverSet 
                (service, status, update_time) 
                VALUES (%s, %s, NOW())
            '''
            cursor.execute(sql, (service, status))
            conn.commit()
            insert_id = cursor.lastrowid
        return jsonify({'id': insert_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# 更新服务状态记录
@server_set_bp.route('/<int:id>', methods=['PUT'])
def update_server_set(id):
    try:
        data = request.get_json()
        updatable_fields = ['service', 'status']
        updates = []
        values = []

        for field in updatable_fields:
            if field in data and data[field] is not None:
                updates.append(f"{field} = %s")
                values.append(data[field])

        if not updates:
            return jsonify({'error': 'No updatable fields provided'}), 400

        values.append(id)
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = f"UPDATE ai114_serverSet SET {', '.join(updates)} WHERE id = %s"
            cursor.execute(sql, values)
            conn.commit()
        return jsonify({
            'success': True,
            'message': 'Update successful',
            'updatedFields': updates
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# 删除服务状态记录
@server_set_bp.route('/<int:id>', methods=['DELETE'])
def delete_server_set(id):
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # 检查记录是否存在
            cursor.execute('SELECT id FROM ai114_serverSet WHERE id = %s', (id,))
            existing = cursor.fetchone()
            if not existing:
                return jsonify({'error': 'Record not found'}), 404

            # 删除记录
            cursor.execute('DELETE FROM ai114_serverSet WHERE id = %s', (id,))
            conn.commit()
        return jsonify({
            'success': True,
            'message': 'Record permanently deleted',
            'deletedId': id
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# 检查所有服务健康状态
@server_set_bp.route('/check_all_services_health', methods=['GET'])
def check_all_services_health():
    """检查所有服务的健康状态"""
    services = [
        {
            'name': '语音识别服务',
            'id': 'ASR',
            'url': 'http://127.0.0.1:8111/asr/health'
        },
        {
            'name': '交互服务',
            'id': 'INTERACTION',
            'url': 'http://127.0.0.1:8222/interaction/health'
        },
        {
            'name': '语音合成服务',
            'id': 'TTS',
            'url': 'http://127.0.0.1:8333/tts/health'
        },
    ]
    
    results = []
    timeout = 3
    
    for service in services:
        try:
            response = requests.get(service['url'], timeout=timeout)
            
            if response.status_code == 200:
                health_data = response.json()
                results.append({
                    'status': 'success',
                    'service': service['id'],
                    'service_name': service['name'],
                    'healthy': health_data.get('status') == 'running',
                    'data': health_data,
                    'timestamp': time.time()
                })
            else:
                results.append({
                    'status': 'error',
                    'service': service['id'],
                    'service_name': service['name'],
                    'healthy': False,
                    'message': f'HTTP {response.status_code}',
                    'timestamp': time.time()
                })
                
        except requests.exceptions.Timeout:
            results.append({
                'status': 'error',
                'service': service['id'],
                'service_name': service['name'],
                'healthy': False,
                'message': '连接超时',
                'timestamp': time.time()
            })
        except requests.exceptions.ConnectionError:
            results.append({
                'status': 'error',
                'service': service['id'],
                'service_name': service['name'],
                'healthy': False,
                'message': '连接失败',
                'timestamp': time.time()
            })
        except Exception as e:
            results.append({
                'status': 'error',
                'service': service['id'],
                'service_name': service['name'],
                'healthy': False,
                'message': str(e),
                'timestamp': time.time()
            })
    
    return jsonify({
        'status': 'success',
        'services': results,
        'timestamp': time.time()
    })