from flask import Blueprint, jsonify, request
from .connectMysql import get_db_connection

# 创建蓝图
train_config_bp = Blueprint('train_config', __name__)
# 查询所有训练配置项
@train_config_bp.route('/', methods=['GET'])
def get_train_configs():
    search = request.args.get('search', '')
    query = 'SELECT * FROM ai114_trainconfig WHERE ref_text LIKE %s OR ref_file LIKE %s'
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

# 查询单个训练配置项
@train_config_bp.route('/<int:id>', methods=['GET'])
def get_train_config(id):
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute('SELECT * FROM ai114_trainconfig WHERE id = %s', (id,))
            row = cursor.fetchone()
            if not row:
                return jsonify({'error': '训练配置项未找到'}), 404
        return jsonify(row)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# 创建新的训练配置项
@train_config_bp.route('/add', methods=['POST'])
def create_train_config():
    try:
        data = request.get_json()
        ref_text = data.get('ref_text')
        ref_file = data.get('ref_file')

        if not all([ref_text, ref_file]):
            return jsonify({'error': 'Missing required parameters'}), 400

        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = '''
                INSERT INTO ai114_trainconfig 
                (ref_text, ref_file) 
                VALUES (%s, %s)
            '''
            cursor.execute(sql, (ref_text, ref_file))
            conn.commit()
            insert_id = cursor.lastrowid
        return jsonify({'id': insert_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# 更新训练配置项
@train_config_bp.route('/<int:id>', methods=['PUT'])
def update_train_config(id):
    try:
        data = request.get_json()
        ref_text = data.get('ref_text')
        ref_file = data.get('ref_file')

        if not any([ref_text, ref_file]):
            return jsonify({'error': 'No updatable fields provided'}), 400

        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = 'UPDATE ai114_trainconfig SET ref_text = %s, ref_file = %s WHERE id = %s'
            cursor.execute(sql, (ref_text, ref_file, id))
            conn.commit()
            if cursor.rowcount == 0:
                return jsonify({'error': '训练配置项未找到'}), 404
        return jsonify({'message': '训练配置项更新成功'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# 删除训练配置项
@train_config_bp.route('/<int:id>', methods=['DELETE'])
def delete_train_config(id):
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute('DELETE FROM ai114_trainconfig WHERE id = %s', (id,))
            conn.commit()
            if cursor.rowcount == 0:
                return jsonify({'error': '训练配置项未找到'}), 404
        return jsonify({'message': '训练配置项删除成功'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()