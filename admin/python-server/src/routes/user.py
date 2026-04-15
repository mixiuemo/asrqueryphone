# user.py
from flask import Blueprint, jsonify, request
from .connectMysql import get_db_connection

# 创建蓝图
user_bp = Blueprint('user', __name__)


def _role_exists(cursor, role_code):
    if not role_code:
        return False
    cursor.execute('SELECT 1 FROM ai114_role WHERE role_code = %s', (role_code,))
    return cursor.fetchone() is not None


# 查询用户列表
@user_bp.route('/', methods=['GET'])
def get_users():
    search_keyword = request.args.get('search', '')
    query = '''
        SELECT u.*, r.role_name AS role_name_display
        FROM ai114_user u
        LEFT JOIN ai114_role r ON u.role = r.role_code
    '''
    params = []

    if search_keyword:
        query += ' WHERE u.username LIKE %s OR u.department LIKE %s OR u.employee_id LIKE %s'
        params.extend([f'%{search_keyword}%', f'%{search_keyword}%', f'%{search_keyword}%'])

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

# 添加新的用户记录
@user_bp.route('/add', methods=['POST'])
def add_user():
    print('阿德hhhhh')
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        employee_id = data.get('employee_id')
        role = data.get('role')
        department = data.get('department')

        if not all([username, password, employee_id, role, department]):
            return jsonify({'error': 'Missing required parameters'}), 400

        conn = get_db_connection()
        with conn.cursor() as cursor:
            if not _role_exists(cursor, role):
                return jsonify({'error': '无效的角色，请先在「用户管理-角色与菜单」中配置该角色'}), 400
            sql = '''
                INSERT INTO ai114_user 
                (username, password, employee_id, role, department) 
                VALUES (%s, %s, %s, %s, %s)
            '''
            cursor.execute(sql, (username, password, employee_id, role, department))
            conn.commit()
            insert_id = cursor.lastrowid
        return jsonify({'id': insert_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# 更新用户记录
@user_bp.route('/<string:employee_id>', methods=['PUT'])
def update_user(employee_id):
    try:
        data = request.get_json()
        updatable_fields = ['username', 'password', 'role', 'department']
        updates = []
        values = []

        for field in updatable_fields:
            if field in data and data[field] is not None:
                updates.append(f"{field} = %s")
                values.append(data[field])

        if not updates:
            return jsonify({'error': 'No updatable fields provided'}), 400

        values.append(employee_id)
        conn = get_db_connection()
        with conn.cursor() as cursor:
            if 'role' in data and data['role'] is not None:
                if not _role_exists(cursor, data['role']):
                    return jsonify({'error': '无效的角色代码'}), 400
            sql = f"UPDATE ai114_user SET {', '.join(updates)} WHERE employee_id = %s"
            cursor.execute(sql, values)
            print('sql::', sql, values)
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

# 删除用户记录
@user_bp.route('/<string:employee_id>', methods=['DELETE'])
def delete_user(employee_id):
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # 检查记录是否存在
            cursor.execute('SELECT employee_id FROM ai114_user WHERE employee_id = %s', (employee_id,))
            existing = cursor.fetchone()
            if not existing:
                return jsonify({'error': 'Record not found'}), 404

            # 删除记录
            cursor.execute('DELETE FROM ai114_user WHERE employee_id = %s', (employee_id,))
            conn.commit()
        return jsonify({
            'success': True,
            'message': 'Record permanently deleted',
            'deletedEmployeeId': employee_id
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()