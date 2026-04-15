from flask import Blueprint, jsonify, request
from .connectMysql import get_db_connection

# 创建蓝图
keywords_bp = Blueprint('keywords', __name__)

# 查询热词
@keywords_bp.route('/', methods=['GET'])
def get_keywords():
    print('get_keywords')
    try:
        # 获取前端传来的搜索关键词
        query = 'SELECT * FROM ai114_hotwords'
        params = []

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

# 合并两个列表并去重，按|分割
def addHotwordFromTele(content, rows, type):
    # 将 content 按 '|' 分割成列表，并去除首尾空格后去重
    arr = list(set([item.strip() for item in content.split('|')]))
    content = ' | '.join(arr)
    if type == 'unitAbbreviation':
        for row in rows:
            if row.get(type):
                # row[type] 有多个值 并用空格隔开的
                for item in row[type].split(' '):
                    param = item.strip()
                    if param not in arr:
                        arr.append(param)
                        content +=' | '+ param
    else:
        for row in rows:
            if row.get(type):
                param = row[type].strip()
                if param not in arr:
                    arr.append(param)
                    content += ' | ' + param

    print('content:', content)
    return content


# 添加热词
@keywords_bp.route('/add', methods=['POST'])
def add_keywords():
    print('add_keywords')
    try:
        data = request.get_json()
        key = data.get('key')
        desc = data.get('desc')
        content = data.get('content')

        sql = "INSERT INTO ai114_hotwords (`key`, `desc`, content) VALUES (%s, %s, %s)"
        print('sql:', sql, [key, desc, content])

        conn = get_db_connection()
        with conn.cursor() as cursor:
            if key == 'HOTWORD_PERSONNEL':
                # 从tele表读取公开项的姓名数据并更新到ai114_hotwords表中
                cursor.execute('SELECT DISTINCT PERSONNEL, surname FROM tele WHERE queryPermission = %s', (1,))
                rows = cursor.fetchall()
                print('tele表公开数据rows:', rows)
                content = content or ""
                content = addHotwordFromTele(content, rows, 'PERSONNEL')
            elif key == 'HOTWORD_UNIT':
                # 从tele表读取公开项的单位数据并更新到ai114_hotwords表中
                cursor.execute('SELECT DISTINCT UNIT FROM tele WHERE queryPermission = %s', (1,))
                rows = cursor.fetchall()
                content = content or ""
                content = addHotwordFromTele(content, rows, 'UNIT')

                # 从tele表读取公开项的“单位简称”数据并更新到ai114_hotwords表中
                cursor.execute('SELECT DISTINCT unitAbbreviation FROM tele WHERE queryPermission = %s', (1,))
                rows2 = cursor.fetchall()
                print('tele表单位简称:', len(rows2))
                content = addHotwordFromTele(content, rows2, 'unitAbbreviation')
            elif key == 'HOTWORD_SURNAME':
                # 从tele表读取姓氏并更新到ai114_hotwords表中
                cursor.execute('SELECT DISTINCT surname FROM tele WHERE surname IS NOT NULL')
                rows = cursor.fetchall()
                content = content or ""
                content = addHotwordFromTele(content, rows, 'surname')
            elif key == 'HOTWORD_POST':
                # 从tele表读取职位并更新到ai114_hotwords表中
                cursor.execute('SELECT DISTINCT JOB FROM tele WHERE JOB IS NOT NULL')
                rows = cursor.fetchall()
                content = content or ""
                content = addHotwordFromTele(content, rows, 'JOB')

            cursor.execute(sql,  [key, desc, content])
            conn.commit()
            insert_id = cursor.lastrowid

        MQ_publisher.publish("HOTWORD热词已更新")
        return jsonify({'id': insert_id}), 201

    except Exception as err:
        if 'Duplicate entry' in str(err):
            print('error1:', str(err))
            return jsonify({'error': str(err), 'errmessage': '热词已存在'}), 401
        print('error:', str(err))
        return jsonify({'error': str(err)}), 500
    finally:
        if 'conn' in locals():
            conn.close()
    
# 更新热词
@keywords_bp.route('/<key>', methods=['PUT'])
def update_keywords(key):
    try:
        # 获取请求体中的 JSON 数据
        data = request.get_json()
        content = data.get('content', "")

        # 检查记录是否存在
        query = "SELECT * FROM ai114_hotwords WHERE `key` = %s"
        print('query:', query, [key])
        conn = get_db_connection()
        with conn.cursor() as cursor:
            print('update_keywords', query, [key])
            cursor.execute(query, [key])
            existing = cursor.fetchall()
            if not existing:
                return jsonify({'error': '记录不存在'}), 404

            # 准备可更新字段
            updatable_fields = ['`desc`', 'content']  # 用反引号包裹 desc 字段
            updates = []
            values = []

            for key1, value in data.items():
                if key1 in updatable_fields and value is not None:
                    updates.append(f"{key1} = %s")
                    values.append(value)

            if not updates:
                return jsonify({'error': '未提供有效更新字段'}), 400

            values.append(key)
            # print('values', values)
            if key == 'HOTWORD_PERSONNEL':
                # 从tele表读取公开项的姓名数据并更新到ai114_hotwords表中
                cursor.execute('SELECT DISTINCT PERSONNEL, surname FROM tele WHERE queryPermission = %s', (1,))
                rows = cursor.fetchall()
                print('tele表公开数据rows:', rows)
                content = addHotwordFromTele(content, rows, 'PERSONNEL')
            elif key == 'HOTWORD_UNIT':
                # 从tele表读取公开项的单位数据并更新到ai114_hotwords表中
                cursor.execute('SELECT DISTINCT UNIT FROM tele WHERE queryPermission = %s', (1,))
                rows = cursor.fetchall()
                print('tele表单位:', len(rows))
                content = addHotwordFromTele(content, rows, 'UNIT')
                
                # 从tele表读取公开项的“单位简称”数据并更新到ai114_hotwords表中
                cursor.execute('SELECT DISTINCT unitAbbreviation FROM tele WHERE queryPermission = %s', (1,))
                rows2 = cursor.fetchall()
                print('tele表单位简称:', len(rows2))
                content = addHotwordFromTele(content, rows2, 'unitAbbreviation')
            elif key == 'HOTWORD_SURNAME':
                # 从tele表读取姓氏并更新到ai114_hotwords表中
                cursor.execute('SELECT DISTINCT surname FROM tele WHERE surname IS NOT NULL')
                rows = cursor.fetchall()
                content = addHotwordFromTele(content, rows, 'surname')
            elif key == 'HOTWORD_POST':
                # 从tele表读取职位并更新到ai114_hotwords表中
                cursor.execute('SELECT DISTINCT JOB FROM tele WHERE JOB IS NOT NULL')
                rows = cursor.fetchall()
                content = addHotwordFromTele(content, rows, 'JOB')

            # 更新 content 字段
            for i, field in enumerate(updatable_fields):
                if field == 'content':
                    if 'content = %s' in updates:
                        index = updates.index('content = %s')
                        values[index] = content
                    else:
                        updates.append('content = %s')
                        values.insert(-1, content)
                    break

            update_query = f"UPDATE ai114_hotwords SET {', '.join(updates)} WHERE `key` = %s"
            print('update_query:', update_query, values)
            cursor.execute(update_query, values)
            conn.commit()

        MQ_publisher.publish("HOTWORD热词已更新")
        print('MQ_publisher:::', MQ_publisher)
        return jsonify({
            'success': True,
            'message': '更新成功',
            'updatedFields': [u.split(' = ')[0] for u in updates]
        }), 200

    except Exception as err:
        print('更新失败:', err)
        return jsonify({
            'success': False,
            'error': '更新失败',
            'details': {
                'code': None,
                'message': str(err),
                'sqlMessage': None
            }
        }), 500
    finally:
        if 'conn' in locals():
            conn.close()

# 删除热词
@keywords_bp.route('/<key>', methods=['DELETE'])
def delete_keywords(key):
    try:
        # 检查记录是否存在
        query = "SELECT * FROM ai114_hotwords WHERE `key` = %s"
        print('query:', query, [key])
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(query, [key])
            existing = cursor.fetchall()
            print('existing:', existing)
            
            if not existing:
                return jsonify({
                    'success': False,
                    'error': '记录不存在'
                }), 404

            # 执行物理删除
            delete_query = 'DELETE FROM ai114_hotwords WHERE `key` = %s'
            cursor.execute(delete_query, [key])
            conn.commit()
            affected_rows = cursor.rowcount

        return jsonify({
            'success': True,
            'message': '记录已永久删除',
            'deletedKey': key,
            'affectedRows': affected_rows
        }), 200

    except Exception as err:
        print('删除失败:', err)
        return jsonify({
            'success': False,
            'error': '删除失败',
            'details': {
                'code': None,
                'message': str(err),
                'sqlMessage': None
            }
        }), 500
    finally:
        if 'conn' in locals():
            conn.close()

def set_MQ(publisher):
    global MQ_publisher # 声明这是一个全局变量
    MQ_publisher = publisher
    print('MQ_publisher: ', MQ_publisher)