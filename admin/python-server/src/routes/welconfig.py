from flask import Blueprint, jsonify, request
from .connectMysql import get_db_connection

# 创建蓝图
wel_config_bp = Blueprint('wel_config', __name__)

# 查询所有欢迎配置项
@wel_config_bp.route('/', methods=['GET'])
def get_wel_configs():
    search = request.args.get('search', '')
    query = 'SELECT * FROM ai114_welconfig WHERE text LIKE %s OR status LIKE %s'
    params = [f'%{search}%', f'%{search}%']

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

# 查询单个欢迎配置项
@wel_config_bp.route('/<int:id>', methods=['GET'])
def get_wel_config(id):
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute('SELECT * FROM ai114_welconfig WHERE id = %s', (id,))
            row = cursor.fetchone()
            if not row:
                return jsonify({'error': '欢迎配置项未找到'}), 404
        return jsonify(row)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# 创建新的欢迎配置项
@wel_config_bp.route('/add', methods=['POST'])
def create_wel_config():
    try:
        data = request.get_json()
        text = data.get('text')
        status = data.get('status')

        # 验证 status 是否为 0 或 1
        if status not in [0, 1]:
            return jsonify({'error': 'status 必须为 0 或 1'}), 400

        # if not all([text, status]):
        #     return jsonify({'error': 'Missing required parameters'}), 400

        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = '''
                INSERT INTO ai114_welconfig 
                (text, status) 
                VALUES (%s, %s)
            '''
            cursor.execute(sql, (text, status))
            conn.commit()
            insert_id = cursor.lastrowid
        return jsonify({'id': insert_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# 更新欢迎配置项
@wel_config_bp.route('/<int:id>', methods=['PUT'])
def update_wel_config(id):
    try:
        data = request.get_json()
        text = data.get('text')
        status = data.get('status')

        # 如果 status 存在，验证其值是否为 0 或 1
        if status is not None and status not in [0, 1]:
            return jsonify({'error': 'status 必须为 0 或 1'}), 400

        conn = get_db_connection()
        with conn.cursor() as cursor:
            # 构建更新语句和参数
            update_fields = []
            params = []
            if text is not None:
                update_fields.append('text = %s')
                params.append(text)
            if status is not None:
                update_fields.append('status = %s')
                params.append(status)
            params.append(id)

            if not update_fields:
                return jsonify({'error': 'No updatable fields provided'}), 400

            sql = f'UPDATE ai114_welconfig SET ' + ', '.join(update_fields) + ' WHERE id = %s'
            cursor.execute(sql, params)
            conn.commit()
            if cursor.rowcount == 0:
                return jsonify({'error': '欢迎配置项未找到'}), 404
        return jsonify({'message': '欢迎配置项更新成功'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# 删除欢迎配置项
@wel_config_bp.route('/<int:id>', methods=['DELETE'])
def delete_wel_config(id):
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute('DELETE FROM ai114_welconfig WHERE id = %s', (id,))
            conn.commit()
            if cursor.rowcount == 0:
                return jsonify({'error': '欢迎配置项未找到'}), 404
        return jsonify({'message': '欢迎配置项删除成功'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()