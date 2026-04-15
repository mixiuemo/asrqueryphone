from flask import Blueprint, jsonify, request
from .connectMysql import get_db_connection

# 创建蓝图
result_bp = Blueprint('result', __name__)

@result_bp.route('/', methods=['GET'])
def get_results():
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            start_date = request.args.get('startDate')
            end_date = request.args.get('endDate')
            query = '''SELECT id, userResult, sysResult, wavFileName, syswavFileName, 
                      resultTime114,
                      channelNumber, callerNumber, callPersonnel, callJob, callUnit 
                      FROM ai114_result'''
            params = []

            conditions = []
            if start_date:
                from datetime import datetime
                start_timestamp = int(datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S').timestamp())
                if end_date:
                    end_timestamp = int(datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S').timestamp())
                    # 兼容秒/毫秒两种存储
                    conditions.append('(resultTime114 BETWEEN %s AND %s OR resultTime114 BETWEEN %s AND %s)')
                    params.extend([start_timestamp, end_timestamp, start_timestamp * 1000, end_timestamp * 1000])
                else:
                    conditions.append('(resultTime114 >= %s OR resultTime114 >= %s)')
                    params.extend([start_timestamp, start_timestamp * 1000])

            if conditions:
                query += ' WHERE ' + ' AND '.join(conditions)
            
            query += ' ORDER BY resultTime114 DESC'

            cursor.execute(query, params)
            rows = cursor.fetchall()
            return jsonify(rows)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# 添加新的结果记录
@result_bp.route('/', methods=['POST'])
def add_result():
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            data = request.get_json()
            name = data.get('name')
            email = data.get('email')
            role = data.get('role')

            if not all([name, email, role]):
                return jsonify({'error': 'Missing required parameters'}), 400

            cursor.execute(
                'INSERT INTO ai114_result (name, email, role) VALUES (%s, %s, %s)',
                (name, email, role)
            )
            conn.commit()
            insert_id = cursor.lastrowid
            return jsonify({'id': insert_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()
