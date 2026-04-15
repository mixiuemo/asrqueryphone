# -*- coding: utf-8 -*-
"""ai114_role：角色及菜单路径权限"""
import json
import re
from flask import Blueprint, jsonify, request
from .connectMysql import get_db_connection

role_bp = Blueprint('role', __name__)

ROLE_CODE_RE = re.compile(r'^[a-z][a-z0-9_]{0,31}$')

# 与前端 menuDefinitions 一致，仅允许配置这些路径
ALLOWED_MENU_PATHS = frozenset({
    '/tele',
    '/paraConfig',
    '/keywords',
    '/serviceStatus',
    '/users',
    '/mqtest',
    '/logs',
    '/trainConfig',
    '/welConfig',
})


def normalize_menu_paths(raw):
    if raw is None:
        return ['/tele']
    if isinstance(raw, list):
        out = [p for p in raw if isinstance(p, str) and p in ALLOWED_MENU_PATHS]
        return sorted(set(out)) if out else ['/tele']
    if isinstance(raw, (bytes, bytearray)):
        try:
            raw = raw.decode('utf-8')
        except Exception:
            return ['/tele']
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
            return normalize_menu_paths(data)
        except json.JSONDecodeError:
            return ['/tele']
    return ['/tele']


def row_to_role(row):
    if not row:
        return None
    paths = normalize_menu_paths(row.get('menu_paths'))
    return {
        'id': row.get('id'),
        'role_code': row.get('role_code'),
        'role_name': row.get('role_name'),
        'menu_paths': paths,
    }


@role_bp.route('/', methods=['GET'])
def list_roles():
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                'SELECT id, role_code, role_name, menu_paths FROM ai114_role ORDER BY id ASC'
            )
            rows = cursor.fetchall()
        return jsonify([row_to_role(r) for r in rows])
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()


@role_bp.route('/add', methods=['POST'])
def add_role():
    try:
        data = request.get_json() or {}
        code = (data.get('role_code') or '').strip().lower()
        name = (data.get('role_name') or '').strip()
        paths = normalize_menu_paths(data.get('menu_paths'))

        if not ROLE_CODE_RE.match(code):
            return jsonify({'error': '角色代码须小写字母开头，仅含小写、数字、下划线，最长32位'}), 400
        if not name:
            return jsonify({'error': '请填写角色名称'}), 400
        if '/tele' not in paths:
            return jsonify({'error': '每个角色至少须包含「通讯录」/tele，否则无法使用系统'}), 400

        blob = json.dumps(paths, ensure_ascii=False)
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                'SELECT id FROM ai114_role WHERE role_code = %s',
                (code,),
            )
            if cursor.fetchone():
                return jsonify({'error': '角色代码已存在'}), 400
            cursor.execute(
                'INSERT INTO ai114_role (role_code, role_name, menu_paths) VALUES (%s, %s, %s)',
                (code, name, blob),
            )
            conn.commit()
            rid = cursor.lastrowid
        return jsonify({'id': rid, 'message': '创建成功'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()


@role_bp.route('/<string:role_code>', methods=['PUT'])
def update_role(role_code):
    try:
        data = request.get_json() or {}
        name = data.get('role_name')
        paths = data.get('menu_paths')

        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                'SELECT id, role_code, role_name, menu_paths FROM ai114_role WHERE role_code = %s',
                (role_code,),
            )
            row = cursor.fetchone()
            if not row:
                return jsonify({'error': '角色不存在'}), 404

            updates = []
            values = []
            if name is not None:
                n = str(name).strip()
                if not n:
                    return jsonify({'error': '角色名称不能为空'}), 400
                updates.append('role_name = %s')
                values.append(n)
            if paths is not None:
                np = normalize_menu_paths(paths)
                if '/tele' not in np:
                    return jsonify({'error': '至少须保留「通讯录」/tele'}), 400
                updates.append('menu_paths = %s')
                values.append(json.dumps(np, ensure_ascii=False))

            if not updates:
                return jsonify({'error': '无更新字段'}), 400

            values.append(role_code)
            sql = f"UPDATE ai114_role SET {', '.join(updates)} WHERE role_code = %s"
            cursor.execute(sql, values)
            conn.commit()
        return jsonify({'message': '更新成功'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()


@role_bp.route('/<string:role_code>', methods=['DELETE'])
def delete_role(role_code):
    if role_code in ('admin',):
        return jsonify({'error': '内置管理员角色不可删除'}), 400
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                'SELECT COUNT(*) AS c FROM ai114_user WHERE role = %s',
                (role_code,),
            )
            cnt = cursor.fetchone()
            n = int(cnt.get('c', 0) or 0) if cnt else 0
            if n:
                return jsonify({'error': '仍有用户使用该角色，无法删除'}), 400
            cursor.execute(
                'DELETE FROM ai114_role WHERE role_code = %s',
                (role_code,),
            )
            conn.commit()
            if cursor.rowcount == 0:
                return jsonify({'error': '角色不存在'}), 404
        return jsonify({'message': '已删除'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()
