from flask import Blueprint, jsonify, request
from .connectMysql import get_db_connection
from .role import normalize_menu_paths

auth_bp = Blueprint('auth', __name__)

# 登录接口
@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({'error': 'Missing username or password'}), 400

        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                '''
                SELECT u.*, r.role_name AS role_display_name, r.menu_paths AS _role_menu_paths
                FROM ai114_user u
                LEFT JOIN ai114_role r ON u.role = r.role_code
                WHERE u.username = %s AND u.password = %s
                ''',
                (username, password),
            )
            user = cursor.fetchone()

        if user:
            raw_paths = user.pop('_role_menu_paths', None)
            user['menu_paths'] = normalize_menu_paths(raw_paths)
            if user.get('role_display_name'):
                user['role_name'] = user['role_display_name']
            print('user:', user)
            return jsonify({
                'code': 200,
                'user': user,
                'message': '登录成功'
            })
        else:
            return jsonify({
                'code': 401,
                'message': '用户名或密码错误'
            }), 401

    except Exception as e:
        print('Login error:', str(e))  
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500
    finally:
        if 'conn' in locals():
            conn.close()