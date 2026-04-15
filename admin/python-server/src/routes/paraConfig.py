from flask import Blueprint, jsonify, request
from .connectMysql import get_db_connection

# 创建蓝图
config_bp = Blueprint('config', __name__)

# 设置MQ
MQ_publisher = None

def set_MQ(mq):
    global MQ_publisher
    MQ_publisher = mq


AI114_MQ_KEYS = frozenset({'ai114_zrg', 'ai114_zj', 'ai114_unknown_policy'})


def _publish_ai114_config_mq(cursor):
    if not MQ_publisher:
        return
    cursor.execute(
        "SELECT name, value FROM ai114_config WHERE name IN ('ai114_zrg', 'ai114_zj', 'ai114_unknown_policy')"
    )
    config_values = {row['name']: row['value'] for row in cursor.fetchall()}
    zrg_value = config_values.get('ai114_zrg', '0')
    zj_value = config_values.get('ai114_zj', '0')
    unk_value = config_values.get('ai114_unknown_policy', '0')
    message = (
        f"UpdateAi114Config:ai114_zrg={zrg_value}:ai114_zj={zj_value}"
        f":ai114_unknown_policy={unk_value}"
    )
    MQ_publisher.publish(message)


# 查询所有配置项
@config_bp.route('/', methods=['GET'])
def get_configs():
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute('SELECT * FROM ai114_config')
            rows = cursor.fetchall()
        return jsonify(rows)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# 查询单个配置项
@config_bp.route('/<int:id>', methods=['GET'])
def get_config(id):
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute('SELECT * FROM ai114_config WHERE id = %s', (id,))
            row = cursor.fetchone()
            if not row:
                return jsonify({'error': '配置项未找到'}), 404
        return jsonify(row)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# 创建新的配置项
@config_bp.route('/add', methods=['POST'])
def create_config():
    try:
        data = request.get_json()
        name = data.get('name')
        value = data.get('value')
        desc = data.get('desc')

        if not all([name, value, desc]):
            return jsonify({'error': 'Missing required parameters'}), 400

        if name == 'ai114_unknown_policy':
            sv = str(value).strip()
            if sv not in ('0', '1', '2'):
                return jsonify({'error': '库外号码策略取值须为 0、1 或 2'}), 400
            value = sv

        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = '''
                INSERT INTO ai114_config 
                (name, value, `desc`) 
                VALUES (%s, %s, %s)
            '''
            cursor.execute(sql, (name, value, desc))
            conn.commit()
            insert_id = cursor.lastrowid
            if name in AI114_MQ_KEYS:
                _publish_ai114_config_mq(cursor)
        return jsonify({'id': insert_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()


# 更新配置项
@config_bp.route('/<int:id>', methods=['PUT'])
def update_config(id):
    try:
        data = request.get_json()
        name = data.get('name')
        value = data.get('value')
        desc = data.get('desc')

        if not any([name, value, desc]):
            return jsonify({'error': 'No updatable fields provided'}), 400

        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute('SELECT name, value FROM ai114_config WHERE id = %s', (id,))
            existing = cursor.fetchone()
            if not existing:
                return jsonify({'error': '配置项未找到'}), 404

            final_name = name if name is not None else existing['name']
            final_value = value if value is not None else existing['value']

            if final_name == 'ai114_unknown_policy':
                sv = str(final_value).strip()
                if sv not in ('0', '1', '2'):
                    return jsonify({'error': '库外号码策略取值须为 0、1 或 2'}), 400
                final_value = sv

            updates = []
            values = []

            if name is not None:
                updates.append('name = %s')
                values.append(name)
            if value is not None:
                updates.append('value = %s')
                values.append(final_value if final_name == 'ai114_unknown_policy' else value)
            if desc is not None:
                updates.append('`desc` = %s')
                values.append(desc)

            values.append(id)

            sql = f"UPDATE ai114_config SET {', '.join(updates)} WHERE id = %s"
            print("update_sql", sql)
            cursor.execute(sql, values)
            conn.commit()
            print("cursor.rowcount", cursor.rowcount)

            cursor.execute('SELECT name FROM ai114_config WHERE id = %s', (id,))
            row_after = cursor.fetchone()
            if row_after and row_after.get('name') in AI114_MQ_KEYS:
                _publish_ai114_config_mq(cursor)

        return jsonify({'message': '配置项更新成功'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# 删除配置项
@config_bp.route('/<int:id>', methods=['DELETE'])
def delete_config(id):
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute('DELETE FROM ai114_config WHERE id = %s', (id,))
            conn.commit()
            if cursor.rowcount == 0:
                return jsonify({'error': '配置项未找到'}), 404
        return jsonify({'message': '配置项删除成功'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()