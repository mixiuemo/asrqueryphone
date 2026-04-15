from flask import Blueprint, jsonify, request
from .connectMysql import get_db_connection

# 创建蓝图
voiceprint_bp = Blueprint('voiceprint', __name__)

# 查询所有声纹识别结果
@voiceprint_bp.route('/', methods=['GET'])
def get_voiceprint_results():
    search = request.args.get('search', '')
    query = 'SELECT * FROM ai114_voiceprintresult WHERE username LIKE %s OR phone LIKE %s'
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

# 查询单个声纹识别结果
@voiceprint_bp.route('/<int:id>', methods=['GET'])
def get_voiceprint_result(id):
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute('SELECT * FROM ai114_voiceprintresult WHERE id = %s', (id,))
            row = cursor.fetchone()
            if not row:
                return jsonify({'error': '声纹识别结果未找到'}), 404
        return jsonify(row)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()