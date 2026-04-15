from flask import Blueprint, jsonify, request, send_file
import pandas as pd
import os
import shutil
import pymysql
from sqlalchemy import create_engine
from .connectMysql import get_db_connection
from pypinyin import pinyin, Style, lazy_pinyin
import re
from itertools import product
import os
import pandas as pd
from flask import send_file
# 创建蓝图
tele_bp = Blueprint('tele', __name__)

# 文件上传配置
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

NAME_PUNCTUATION_PATTERN = re.compile(r"[\u00B7\u2022\u2027\u30FB\u2219\.．。]")

def pinyin_tone3(chars, heteronym=False):
    """兼容不同 pypinyin 版本：优先使用 neutral_tone_with_five。"""
    kwargs = {
        "style": Style.TONE3,
        "heteronym": heteronym
    }
    try:
        return pinyin(chars, neutral_tone_with_five=True, **kwargs)
    except TypeError:
        return pinyin(chars, **kwargs)

def pinyin_normal(chars, heteronym=False):
    """无音调拼音（严格使用当前拼音生成方法的无音调版本）。"""
    kwargs = {
        "style": Style.NORMAL,
        "heteronym": heteronym
    }
    return pinyin(chars, **kwargs)

def normalize_text_value(value, remove_name_punct=False):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ''
    text = str(value).lstrip()
    if remove_name_punct:
        text = NAME_PUNCTUATION_PATTERN.sub('', text)
    return text

def get_surname_from_name(name):
    normalized_name = normalize_text_value(name, remove_name_punct=True)
    return normalized_name[0] if normalized_name else ''

# 文件处理逻辑
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'xls', 'xlsx'}

# 文件清理逻辑
def clean_up_file(file_path):
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        print(f"File cleanup failed: {e}")

# 导入通讯录
@tele_bp.route('/importtele', methods=['POST'])
def import_tele():
    required_columns = ['单位(114)', '单位简称', '姓名(114)', '职位', '查询级别', '电话类型', '电话号码']
    file = request.files.get('file')
    if not file or not allowed_file(file.filename):
        return jsonify({'status': 'error', 'message': '未收到文件或文件类型不支持'}), 400

    try:
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)

        df = pd.read_excel(file_path)

        column_mapping = {
            '单位(114)': 'UNIT',
            '单位简称': 'unitAbbreviation',
            '姓名(114)': 'PERSONNEL',
            '职位': 'JOB',
            '查询级别': 'queryPermission',
            '电话类型': 'telephoneType',
            '电话号码': 'TELE_CODE'
        }

        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})

        default_values = {
            'UNIT': '',
            'unitAbbreviation': '',
            'PERSONNEL': '',
            'JOB': '',
            'queryPermission': 1,
            'telephoneType': '',
            'TELE_CODE': ''
        }

        for column, default_value in default_values.items():
            if column not in df.columns:
                df[column] = default_value
            else:
                df[column] = df[column].fillna(default_value)

        text_columns = ['UNIT', 'unitAbbreviation', 'PERSONNEL', 'JOB', 'telephoneType', 'TELE_CODE']
        for column in text_columns:
            df[column] = df[column].apply(
                lambda x: normalize_text_value(x, remove_name_punct=(column == 'PERSONNEL'))
            )

        # SURNAME from first character of PERSONNEL
        df['SURNAME'] = df['PERSONNEL'].apply(get_surname_from_name)

        conn = get_db_connection()
        try:
            conn.begin()
            try:
                for _, row in df.iterrows():
                    values = (
                        row['unitAbbreviation'],
                        row['queryPermission'],
                        row['SURNAME'],
                        row['telephoneType'],
                        row['TELE_CODE'],
                        row['JOB'],
                        row['UNIT'],
                        row['PERSONNEL']
                    )

                    sql = '''
                        INSERT INTO tele 
                        (unitAbbreviation, queryPermission, SURNAME, telephoneType, TELE_CODE, JOB, UNIT, PERSONNEL)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    '''

                    conn.cursor().execute(sql, values)

                conn.commit()
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                conn.close()

        except Exception as e:
            print(f"importtele db error: {e}")
            return jsonify({'status': 'error', 'message': '数据库写入失败'}), 500

        clean_up_file(file_path)
        updatekw()
        return jsonify({
            'status': 'success',
            'message': '导入成功，请执行“拼音转换”和“数据写入”以完成模板更新',
            'imported': len(df),
            'sample': df.head(3).to_dict(orient='records')
        })

    except Exception as e:
        print(f"importtele error: {e}")
        clean_up_file(file_path)
        return jsonify({'status': 'error', 'message': str(e)}), 500


@tele_bp.route('/template', methods=['GET'])    
def download_template():
    try:
        # 创建模板数据
        template_data = {
            '单位(114)': ['上海新殿光技术部'],
            '单位简称': ['新殿光 技术部'],
            '姓名(114)': ['张小龙'],
            '职位': ['工程师'],
            '查询级别': [3],
            '电话类型': ['移动电话'],
            '电话号码': ['18210642434'],
        }

        # 创建 DataFrame
        df = pd.DataFrame(template_data)

        # 指定文件保存的绝对路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(current_dir, 'tele_template.xlsx')

        # 确保目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # 保存为 Excel 文件
        df.to_excel(output_path, index=False, engine='openpyxl')

        # 发送文件
        return send_file(output_path, as_attachment=True, download_name='tele_template.xlsx')

    except Exception as e:
        print(f"Error generating template: {e}")
        return jsonify({'status': 'error', 'message': '模板生成失败'}), 500

# 查询通讯录
@tele_bp.route('/', methods=['GET'])
def get_tele():
    search_keyword = request.args.get('search', '')
    query = 'SELECT * FROM tele'
    params = []

    if search_keyword:
        # 支持搜索的字段：用户姓名、单位、单位简称、电话号码、职位、部门等
        search_conditions = [
            'PERSONNEL LIKE %s',      
            'UNIT LIKE %s',           
            'unitAbbreviation LIKE %s',
            'TELE_CODE LIKE %s',      
            'JOB LIKE %s',            
        ]
        
        query += ' WHERE (' + ' OR '.join(search_conditions) + ')'
        # 为每个搜索条件添加相同的搜索关键词
        params.extend([f'%{search_keyword}%'] * len(search_conditions))

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

# 添加新的通讯录记录
@tele_bp.route('/add', methods=['POST'])
def add_tele():
    try:
        data = request.get_json()
        personnel = normalize_text_value(data.get('PERSONNEL', ''), remove_name_punct=True)
        surname = normalize_text_value(data.get('surname', ''), remove_name_punct=True) or get_surname_from_name(personnel)
        sql = '''
            INSERT INTO tele 
            (telephoneType, USER, TELE_CODE, JOB, UNIT, PERSONNEL, queryPermission, unitAbbreviation, surname) 
            VALUES (%s, %s, %s, %s, %s, %s, 1, %s, %s)
        '''
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(sql, (
                normalize_text_value(data.get('telephoneType', '')),
                data.get('USER', ''),
                normalize_text_value(data.get('TELE_CODE', '')),
                normalize_text_value(data.get('JOB', '')),
                normalize_text_value(data.get('UNIT', '')),
                personnel,
                normalize_text_value(data.get('unitAbbreviation', '')),
                surname
            ))
            conn.commit()
            insert_id = cursor.lastrowid
            
            cursor.execute("SELECT * FROM tele WHERE NUMBER = %s", (insert_id,))
            new_record = cursor.fetchone()
            
            if new_record:
                userPY = process_name_to_pinyin(new_record['PERSONNEL'])
                surPY = process_name_to_pinyin(new_record['surname'])
                departmentPY = process_text_to_pinyin(new_record['UNIT'])
                jobPY = process_name_to_pinyin(new_record['JOB'])
                unitAbbreviationPY = process_text_to_pinyin(new_record['unitAbbreviation'])
                userPY_no_tone = process_name_to_pinyin_no_tone(new_record['PERSONNEL'])
                surPY_no_tone = process_name_to_pinyin_no_tone(new_record['surname'])
                departmentPY_no_tone = process_text_to_pinyin_no_tone(new_record['UNIT'])
                jobPY_no_tone = process_name_to_pinyin_no_tone(new_record['JOB'])
                unitAbbreviationPY_no_tone = process_text_to_pinyin_no_tone(new_record['unitAbbreviation'])
                
                update_pinyin_sql = """
                    UPDATE tele
                    SET userPY = %s,
                        departmentPY = %s,
                        surPY = %s,
                        jobPY = %s,
                        unitAbbreviationPY = %s,
                        userPY_no_tone = %s,
                        surPY_no_tone = %s,
                        departmentPY_no_tone = %s,
                        jobPY_no_tone = %s,
                        unitAbbreviationPY_no_tone = %s
                    WHERE NUMBER = %s
                """
                cursor.execute(update_pinyin_sql, (
                    userPY, 
                    departmentPY, 
                    surPY, 
                    jobPY, 
                    unitAbbreviationPY, 
                    userPY_no_tone,
                    surPY_no_tone,
                    departmentPY_no_tone,
                    jobPY_no_tone,
                    unitAbbreviationPY_no_tone,
                    insert_id
                ))
                conn.commit()
        
        updatekw()
        try:
            write_data_to_json()
        except Exception as e:
            print(f"write_data_to_json failed after add: {e}")
        return jsonify({'id': insert_id, 'message': '添加成功并完成拼音转换'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# 更新通讯录记录
@tele_bp.route('/<string:number>', methods=['PUT'])
def update_tele(number):
    try:
        data = request.get_json()
        updatable_fields = [
            'telephoneType', 'USER', 'TELE_CODE',
            'JOB', 'UNIT', 'PERSONNEL', 'Tele_GROUP',
            'queryPermission', 'unitAbbreviation', 'surname'
        ]
        updates = []
        values = []
        text_fields = {'telephoneType', 'TELE_CODE', 'JOB', 'UNIT', 'PERSONNEL', 'unitAbbreviation'}
        surname_updated = False

        for field in updatable_fields:
            if field in data and data[field] is not None:
                updates.append(f"{field} = %s")
                if field == 'PERSONNEL':
                    values.append(normalize_text_value(data[field], remove_name_punct=True))
                elif field == 'surname':
                    values.append(normalize_text_value(data[field], remove_name_punct=True))
                    surname_updated = True
                elif field in text_fields:
                    values.append(normalize_text_value(data[field]))
                else:
                    values.append(data[field])

        if 'PERSONNEL' in data and not surname_updated:
            updates.append("surname = %s")
            values.append(get_surname_from_name(data.get('PERSONNEL', '')))

        if not updates:
            return jsonify({'error': 'No updatable fields provided'}), 400

        values.append(number)
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = f"UPDATE tele SET {', '.join(updates)} WHERE NUMBER = %s"
            cursor.execute(sql, values)
            conn.commit()
            
            cursor.execute("SELECT * FROM tele WHERE NUMBER = %s", (number,))
            updated_record = cursor.fetchone()
            
            if updated_record:
                userPY = process_name_to_pinyin(updated_record['PERSONNEL'])
                surPY = process_name_to_pinyin(updated_record['surname'])
                departmentPY = process_text_to_pinyin(updated_record['UNIT'])
                jobPY = process_name_to_pinyin(updated_record['JOB'])
                unitAbbreviationPY = process_text_to_pinyin(updated_record['unitAbbreviation'])
                userPY_no_tone = process_name_to_pinyin_no_tone(updated_record['PERSONNEL'])
                surPY_no_tone = process_name_to_pinyin_no_tone(updated_record['surname'])
                departmentPY_no_tone = process_text_to_pinyin_no_tone(updated_record['UNIT'])
                jobPY_no_tone = process_name_to_pinyin_no_tone(updated_record['JOB'])
                unitAbbreviationPY_no_tone = process_text_to_pinyin_no_tone(updated_record['unitAbbreviation'])
                
                update_pinyin_sql = """
                    UPDATE tele
                    SET userPY = %s,
                        departmentPY = %s,
                        surPY = %s,
                        jobPY = %s,
                        unitAbbreviationPY = %s,
                        userPY_no_tone = %s,
                        surPY_no_tone = %s,
                        departmentPY_no_tone = %s,
                        jobPY_no_tone = %s,
                        unitAbbreviationPY_no_tone = %s
                    WHERE NUMBER = %s
                """
                cursor.execute(update_pinyin_sql, (
                    userPY, 
                    departmentPY, 
                    surPY, 
                    jobPY, 
                    unitAbbreviationPY, 
                    userPY_no_tone,
                    surPY_no_tone,
                    departmentPY_no_tone,
                    jobPY_no_tone,
                    unitAbbreviationPY_no_tone,
                    number
                ))
                conn.commit()
                try:
                    write_data_to_json()
                except Exception as e:
                    print(f"write_data_to_json failed after update: {e}")
        
        updatekw()
        return jsonify({
            'success': True,
            'message': 'Update successful and pinyin updated',
            'updatedFields': updates
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# 删除通讯录记录
@tele_bp.route('/<string:number>', methods=['DELETE'])
def delete_tele(number):
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute('SELECT NUMBER FROM tele WHERE NUMBER = %s', (number,))
            existing = cursor.fetchone()
            if not existing:
                return jsonify({'error': 'Record not found'}), 404

            cursor.execute('DELETE FROM tele WHERE NUMBER = %s', (number,))
            conn.commit()
        return jsonify({
            'success': True,
            'message': 'Record permanently deleted',
            'deletedNumber': number
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@tele_bp.route('/clear_all', methods=['POST'])
def clear_all_tele():
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute('SELECT COUNT(*) AS total FROM tele')
            count_row = cursor.fetchone() or {}
            total = int(count_row.get('total', 0))
            cursor.execute('DELETE FROM tele')
            conn.commit()
        return jsonify({
            'success': True,
            'message': f'已清空通讯录数据，共删除 {total} 条记录',
            'deleted': total
        })
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# 批量导入
@tele_bp.route('/import', methods=['POST'])
def import_bulk():
    try:
        data = request.get_json()
        conn = get_db_connection()
        for item in data:
            sql = '''
                INSERT INTO tele 
                (NUMBER, PERSONNEL, TELE_CODE, JOB, UNIT, unitAbbreviation) 
                VALUES (%s, %s, %s, %s, %s, %s)
            '''
            conn.cursor().execute(sql, (
                item.get('NUMBER'),
                item.get('PERSONNEL'),
                item.get('TELE_CODE'),
                item.get('JOB'),
                item.get('UNIT'),
                item.get('unitAbbreviation')
            ))
        conn.commit()
        return jsonify({'success': True}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# 辅助函数：更新关键词
def updatekw():
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute('SELECT content FROM ai114_hotwords WHERE `key` = %s LIMIT 1', ('HOTWORD_PERSONNEL',))
            hotword_row = cursor.fetchone()
            cursor.execute('SELECT DISTINCT PERSONNEL, surname FROM tele WHERE queryPermission = 1')
            rows = cursor.fetchall()

            content = ''
            if hotword_row and 'content' in hotword_row:
                content = hotword_row['content']

            arr = content.split('|')
            arr = list(set([item.strip() for item in arr]))
            content = ' | '.join(arr)

            for row in rows:
                if row['PERSONNEL'] and row['PERSONNEL'].strip() not in arr:
                    arr.append(row['PERSONNEL'].strip())
                    content += ' | ' + row['PERSONNEL'].strip()

            sql = "UPDATE ai114_hotwords SET `desc` = %s, content = %s WHERE `key` = %s"
            cursor.execute(sql, ('姓名', content, 'HOTWORD_PERSONNEL'))

            cursor.execute('SELECT content FROM ai114_hotwords WHERE `key` = %s LIMIT 1', ('HOTWORD_SURNAME',))
            surname_row = cursor.fetchone()

            surname_content = ''
            if surname_row and 'content' in surname_row:
                surname_content = surname_row['content']

            surname_arr = surname_content.split('|')
            surname_arr = list(set([item.strip() for item in surname_arr]))

            for row in rows:
                surname = row.get('surname') or get_surname_from_name(row.get('PERSONNEL', ''))
                if surname and surname.strip() not in surname_arr:
                    surname_arr.append(surname.strip())
                    surname_content += ' | ' + surname.strip()

            cursor.execute(sql, ('姓氏', surname_content, 'HOTWORD_SURNAME'))

            conn.commit()
    except Exception as e:
        print(f"updatekw failed: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

# 批量转换拼音
@tele_bp.route('/update_pinyin', methods=['POST'])
def update_pinyin():
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # 获取所有记录
            cursor.execute("SELECT NUMBER, PERSONNEL, UNIT, surname, JOB, unitAbbreviation FROM tele WHERE PERSONNEL IS NOT NULL AND PERSONNEL != ''")
            rows = cursor.fetchall()
            
            updated_count = 0
            for row in rows:
                # 处理各个字段的拼音
                userPY = process_name_to_pinyin(row['PERSONNEL'])
                surPY = process_name_to_pinyin(row['surname'])
                departmentPY = process_text_to_pinyin(row['UNIT'])
                jobPY = process_name_to_pinyin(row['JOB'])  # 职务也使用多音字处理
                unitAbbreviationPY = process_text_to_pinyin(row['unitAbbreviation'])
                userPY_no_tone = process_name_to_pinyin_no_tone(row['PERSONNEL'])
                surPY_no_tone = process_name_to_pinyin_no_tone(row['surname'])
                departmentPY_no_tone = process_text_to_pinyin_no_tone(row['UNIT'])
                jobPY_no_tone = process_name_to_pinyin_no_tone(row['JOB'])
                unitAbbreviationPY_no_tone = process_text_to_pinyin_no_tone(row['unitAbbreviation'])
                
                # 更新数据库
                update_sql = """
                    UPDATE tele
                    SET userPY = %s,
                        departmentPY = %s,
                        surPY = %s,
                        jobPY = %s,
                        unitAbbreviationPY = %s,
                        userPY_no_tone = %s,
                        surPY_no_tone = %s,
                        departmentPY_no_tone = %s,
                        jobPY_no_tone = %s,
                        unitAbbreviationPY_no_tone = %s
                    WHERE NUMBER = %s
                """
                cursor.execute(update_sql, (
                    userPY, 
                    departmentPY, 
                    surPY, 
                    jobPY, 
                    unitAbbreviationPY, 
                    userPY_no_tone,
                    surPY_no_tone,
                    departmentPY_no_tone,
                    jobPY_no_tone,
                    unitAbbreviationPY_no_tone,
                    row['NUMBER']
                ))
                updated_count += 1
            
            conn.commit()
            
            return jsonify({
                'status': 200,
                'message': f'Successfully updated pinyin for {updated_count} records',
                'details': {
                    'total_processed': updated_count
                }
            })
            
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
        
    finally:
        if 'conn' in locals():
            conn.close()

@tele_bp.route('/write_data_to_json', methods=['POST'])
def write_data_to_json():
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT NUMBER, PERSONNEL, UNIT, JOB, surname, unitAbbreviation,
                       userPY, surPY, departmentPY, jobPY, unitAbbreviationPY,
                       userPY_no_tone, surPY_no_tone, departmentPY_no_tone, jobPY_no_tone, unitAbbreviationPY_no_tone,
                       TELE_CODE, telephoneType, queryPermission
                FROM tele 
                WHERE PERSONNEL IS NOT NULL 
                AND PERSONNEL != ''
                ORDER BY NUMBER
            """)
            rows = cursor.fetchall()

            query_templates = []
            query_templates_no_tone = []

            def expand_pinyin_variants(pinyin_str):
                if not pinyin_str:
                    return []
                variants = [variant.strip() for variant in pinyin_str.split('|')]
                return [v for v in variants if v]

            def build_templates(templates, variants_map):
                results = []
                for tpl in templates:
                    keys = re.findall(r"\{(\w+)\}", tpl)
                    if not keys:
                        continue
                    variants_lists = []
                    for key in keys:
                        variants = variants_map.get(key, [])
                        if not variants:
                            variants_lists = []
                            break
                        variants_lists.append(variants)
                    if not variants_lists:
                        continue
                    for combo in product(*variants_lists):
                        parts = [str(value).strip() for value in combo if str(value).strip()]
                        if not parts:
                            continue
                        rendered = "".join([f"{{{part}}}" for part in parts])
                        results.append(rendered)
                return results

            phrase_templates = [
                "{unit}{name}{job}",
                "{unit}{surname}{job}",
                "{unit}{name}",
                "{unit}{job}",
                "{unit}{de}{name}{job}",
                "{unit}{de}{surname}{job}",
                "{unit}{de}{name}",
                "{unit}{de}{job}",
                "{name}{job}",
                "{name}{surname}{job}",
                "{surname}{job}",
                "{name}"
            ]

            for row in rows:
                name_py_variants = expand_pinyin_variants(row.get('userPY'))
                dept_py_variants = expand_pinyin_variants(row.get('departmentPY'))
                job_py_variants = expand_pinyin_variants(row.get('jobPY'))
                surname_py_variants = expand_pinyin_variants(row.get('surPY'))
                unit_abbr_py_variants = expand_pinyin_variants(row.get('unitAbbreviationPY'))

                if not name_py_variants and row.get('PERSONNEL'):
                    name_py_variants = expand_pinyin_variants(process_name_to_pinyin(row['PERSONNEL']))
                if not surname_py_variants:
                    if row.get('surname'):
                        surname_py_variants = expand_pinyin_variants(process_name_to_pinyin(row['surname']))
                    elif row.get('PERSONNEL'):
                        surname_py_variants = [get_surname_from_name(row.get('PERSONNEL', ''))]
                if not dept_py_variants and row.get('UNIT'):
                    dept_py_variants = expand_pinyin_variants(process_text_to_pinyin(row['UNIT']))
                if not job_py_variants and row.get('JOB'):
                    job_py_variants = expand_pinyin_variants(process_name_to_pinyin(row['JOB']))
                if not unit_abbr_py_variants and row.get('unitAbbreviation'):
                    unit_abbr_py_variants = expand_pinyin_variants(process_text_to_pinyin(row['unitAbbreviation']))

                name_py_variants_no_tone = expand_pinyin_variants(row.get('userPY_no_tone'))
                dept_py_variants_no_tone = expand_pinyin_variants(row.get('departmentPY_no_tone'))
                job_py_variants_no_tone = expand_pinyin_variants(row.get('jobPY_no_tone'))
                surname_py_variants_no_tone = expand_pinyin_variants(row.get('surPY_no_tone'))
                unit_abbr_py_variants_no_tone = expand_pinyin_variants(row.get('unitAbbreviationPY_no_tone'))

                if not name_py_variants_no_tone and row.get('PERSONNEL'):
                    name_py_variants_no_tone = expand_pinyin_variants(process_name_to_pinyin_no_tone(row['PERSONNEL']))
                if not surname_py_variants_no_tone:
                    if row.get('surname'):
                        surname_py_variants_no_tone = expand_pinyin_variants(process_name_to_pinyin_no_tone(row['surname']))
                    elif row.get('PERSONNEL'):
                        surname_py_variants_no_tone = [get_surname_from_name(row.get('PERSONNEL', ''))]
                if not dept_py_variants_no_tone and row.get('UNIT'):
                    dept_py_variants_no_tone = expand_pinyin_variants(process_text_to_pinyin_no_tone(row['UNIT']))
                if not job_py_variants_no_tone and row.get('JOB'):
                    job_py_variants_no_tone = expand_pinyin_variants(process_name_to_pinyin_no_tone(row['JOB']))
                if not unit_abbr_py_variants_no_tone and row.get('unitAbbreviation'):
                    unit_abbr_py_variants_no_tone = expand_pinyin_variants(process_text_to_pinyin_no_tone(row['unitAbbreviation']))

                unit_py_variants = list({*dept_py_variants, *unit_abbr_py_variants})
                unit_py_variants_no_tone = list({*dept_py_variants_no_tone, *unit_abbr_py_variants_no_tone})

                variants_map = {
                    "unit": unit_py_variants,
                    "name": name_py_variants,
                    "surname": surname_py_variants,
                    "job": job_py_variants,
                    "de": ["de5"]
                }
                query_templates.extend(build_templates(phrase_templates, variants_map))

                variants_map_no_tone = {
                    "unit": unit_py_variants_no_tone,
                    "name": name_py_variants_no_tone,
                    "surname": surname_py_variants_no_tone,
                    "job": job_py_variants_no_tone,
                    "de": ["de"]
                }
                query_templates_no_tone.extend(build_templates(phrase_templates, variants_map_no_tone))

            seen = set()
            unique_templates = []
            for template in query_templates:
                if template not in seen:
                    seen.add(template)
                    unique_templates.append(template)

            seen_no_tone = set()
            unique_templates_no_tone = []
            for template in query_templates_no_tone:
                if template not in seen_no_tone:
                    seen_no_tone.add(template)
                    unique_templates_no_tone.append(template)

            import json
            import os
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.join(current_dir, '..', '..', '..', '..')
            query_templates_file_path = os.path.join(project_root, 'asr', 'Interaction', 'data', 'query_templates.json')
            query_templates_no_tone_file_path = os.path.join(project_root, 'asr', 'Interaction', 'data', 'query_templates_no_tone.json')
            os.makedirs(os.path.dirname(query_templates_file_path), exist_ok=True)
            with open(query_templates_file_path, 'w', encoding='utf-8') as f:
                json.dump(unique_templates, f, ensure_ascii=False, indent=2)
            with open(query_templates_no_tone_file_path, 'w', encoding='utf-8') as f:
                json.dump(unique_templates_no_tone, f, ensure_ascii=False, indent=2)

            user_details = []
            cursor.execute("""
                SELECT NUMBER, PERSONNEL, DEPARTMENT, UNIT, surname, JOB, unitAbbreviation, 
                       userPY, departmentPY, surPY, jobPY, unitAbbreviationPY,
                       userPY_no_tone, surPY_no_tone, departmentPY_no_tone, jobPY_no_tone, unitAbbreviationPY_no_tone,
                       TELE_CODE, telephoneType, queryPermission
                FROM tele 
                WHERE PERSONNEL IS NOT NULL 
                AND PERSONNEL != ''
                ORDER BY NUMBER
            """)
            user_rows = cursor.fetchall()

            for row in user_rows:
                user_detail = {
                    "NUMBER": row['NUMBER'],
                    "PERSONNEL": row['PERSONNEL'] or '',
                    "UNIT": row['UNIT'] or '',
                    "TELE_CODE": row['TELE_CODE'] or '',
                    "JOB": row['JOB'] or '',
                    "telephoneType": row['telephoneType'] or row['DEPARTMENT'],
                    "surname": row['surname'] or '',
                    "userPY": row['userPY'] or '',
                    "surPY": row['surPY'] or '',
                    "departmentPY": row['departmentPY'] or '',
                    "jobPY": row['jobPY'] or '',
                    "unitAbbreviation": row['unitAbbreviation'] or '',
                    "unitAbbreviationPY": row['unitAbbreviationPY'] or '',
                    "userPY_no_tone": row.get('userPY_no_tone') or '',
                    "surPY_no_tone": row.get('surPY_no_tone') or '',
                    "departmentPY_no_tone": row.get('departmentPY_no_tone') or '',
                    "jobPY_no_tone": row.get('jobPY_no_tone') or '',
                    "unitAbbreviationPY_no_tone": row.get('unitAbbreviationPY_no_tone') or '',
                    "queryPermission": row['queryPermission']
                }
                user_details.append(user_detail)

            user_details_file_path = os.path.join(project_root, 'asr', 'Interaction', 'data', 'phone_database.json')
            os.makedirs(os.path.dirname(user_details_file_path), exist_ok=True)
            with open(user_details_file_path, 'w', encoding='utf-8') as f:
                json.dump(user_details, f, ensure_ascii=False, indent=2)

            return jsonify({
                'status': 200,
                'message': f'Successfully updated {len(unique_templates)} query templates, {len(unique_templates_no_tone)} no-tone templates, and {len(user_details)} user details',
                'details': {
                    'total_templates': len(unique_templates),
                    'total_users': len(user_details),
                    'query_templates_count': len(unique_templates),
                    'query_templates_no_tone_count': len(unique_templates_no_tone),
                    'user_details_count': len(user_details)
                }
            })

    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
    finally:
        if 'conn' in locals():
            conn.close()


@tele_bp.route('/write_hotwords', methods=['POST'])
def write_hotwords():
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT UNIT, PERSONNEL, JOB, unitAbbreviation 
                FROM tele 
                WHERE (UNIT IS NOT NULL AND UNIT != '' 
                     OR PERSONNEL IS NOT NULL AND PERSONNEL != ''
                     OR JOB IS NOT NULL AND JOB != ''
                     OR unitAbbreviation IS NOT NULL AND unitAbbreviation != '')
            """)
            rows = cursor.fetchall()
            
            hotwords = []
            
            for row in rows:
                if row['UNIT'] and row['UNIT'].strip():
                    hotwords.append(row['UNIT'].strip())
                
                if row['unitAbbreviation'] and row['unitAbbreviation'].strip():
                    abbreviations = [abbr.strip() for abbr in row['unitAbbreviation'].split() if abbr.strip()]
                    hotwords.extend(abbreviations)
                
                if row['PERSONNEL'] and row['PERSONNEL'].strip():
                    hotwords.append(row['PERSONNEL'].strip())
                
                if row['JOB'] and row['JOB'].strip():
                    hotwords.append(row['JOB'].strip())
            
            default_hotwords = [
                '查下', '查一下', '转下', '转一下', '接下', '接一下', 
                '找下', '找一下', '播下', '播一下', '打下', '打一下'
            ]
            
            # 合并数据库热词和默认热词
            all_hotwords = hotwords + default_hotwords
            unique_hotwords = sorted(list(set(all_hotwords)))
            
            import os
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.join(current_dir, '..', '..', '..', '..')
            txt_file_path = os.path.join(project_root, 'asr', 'identifyPro', 'hotwords.txt')
            os.makedirs(os.path.dirname(txt_file_path), exist_ok=True)
            with open(txt_file_path, 'w', encoding='utf-8') as f:
                for word in unique_hotwords:
                    f.write(word + '\n')
            
            return jsonify({
                'status': 200,
                'message': f'Successfully wrote {len(unique_hotwords)} hotwords to file',
                'details': {
                    'total_hotwords': len(unique_hotwords),
                    'file_path': txt_file_path
                }
            })
            
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
    finally:
        if 'conn' in locals():
            conn.close()

@tele_bp.route('/read_hotwords', methods=['GET'])
def read_hotwords():
    try:
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.join(current_dir, '..', '..', '..', '..')
        txt_file_path = os.path.join(project_root, 'asr', 'identifyPro', 'hotwords.txt')
        
        if not os.path.exists(txt_file_path):
            return jsonify({
                'status': 200,
                'message': '热词文件不存在',
                'details': {
                    'hotwords': [],
                    'total_hotwords': 0,
                    'file_path': txt_file_path
                }
            })
        
        with open(txt_file_path, 'r', encoding='utf-8') as f:
            hotwords = [line.strip() for line in f.readlines() if line.strip()]
        
        return jsonify({
            'status': 200,
            'message': f'成功读取 {len(hotwords)} 个热词',
            'details': {
                'hotwords': hotwords,
                'total_hotwords': len(hotwords),
                'file_path': txt_file_path
            }
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# 拼音转换函数
def to_pinyin(text):
    if not text:
        return ''
    return ''.join([item[0] for item in pinyin_tone3(text)])
# 处理多音字的人名拼音
def to_pinyin_name_heteronym(text):
    if not text:
        return ''
    pinyins = pinyin_tone3(text, heteronym=True)
    combinations = list(product(*pinyins))
    results = []
    for combo in combinations:
        # 每个字用空格分开
        result = ' '.join(combo)
        results.append(result)
    # 多种读法用|分开
    return ' | '.join(sorted(set(results)))

def to_pinyin_name_heteronym_no_tone(text):
    if not text:
        return ''
    pinyins = pinyin_normal(text, heteronym=True)
    combinations = list(product(*pinyins))
    results = []
    for combo in combinations:
        result = ' '.join(combo)
        results.append(result)
    return ' | '.join(sorted(set(results)))
# 数字转中文映射
digit_map = {'0': '零', '1': '一', '2': '二', '3': '三', '4': '四', 
            '5': '五', '6': '六', '7': '七', '8': '八', '9': '九'}
digit_map_yao = {**digit_map, '1': '幺'}

def num_to_chinese(numstr):
    if not numstr:
        return ''
    return ''.join([digit_map[d] for d in numstr])

def num_to_chinese_yao(numstr):
    if not numstr:
        return ''
    return ''.join([digit_map_yao[d] for d in numstr])

def process_number(numstr):
    results = []
    results.append(numstr)
    
    # 处理单个数字
    if len(numstr) == 1:
        results.append(num_to_chinese(numstr))
        if numstr == '1':
            results.append(num_to_chinese_yao(numstr))
    # 处理两位数字
    elif len(numstr) == 2:
        results.append(num_to_chinese(numstr))
        if numstr[0] == '1':
            if numstr[1] != '0':
                results.append('十' + digit_map[numstr[1]])
            else:
                results.append('十')
        else:
            if numstr[1] != '0':
                results.append(digit_map[numstr[0]] + '十' + digit_map[numstr[1]])
            else:
                results.append(digit_map[numstr[0]] + '十')
        if '1' in numstr:
            results.append(num_to_chinese_yao(numstr))
    # 处理三位及以上数字
    elif len(numstr) >= 3:
        results.append(num_to_chinese(numstr))
        if '1' in numstr:
            results.append(num_to_chinese_yao(numstr))
    
    return list(set(results))

def process_text_with_numbers(text):
    if not text:
        return [text]
    
    number_positions = []
    # 修改正则表达式以匹配单个数字
    for match in re.finditer(r'\d+', text):
        start, end = match.span()
        numstr = match.group()
        # 对所有数字进行处理
        variants = process_number(numstr)
        number_positions.append((start, end, numstr, variants))
    
    if not number_positions:
        return [text]
    
    results = [text]
    
    for start, end, numstr, variants in number_positions:
        new_results = []
        for current_text in results:
            for variant in variants:
                new_text = current_text[:start] + variant + current_text[end:]
                new_results.append(new_text)
        results = new_results
    
    return list(set(results))

def process_name_to_pinyin(text):
    if not text:
        return ''

    normalized_text = normalize_text_value(text, remove_name_punct=True)
    text_variants = process_text_with_numbers(normalized_text)
    results = set()
    for variant in text_variants:
        heteronym_result = to_pinyin_name_heteronym(variant)
        # 将结果按|分割，每个部分作为一个完整的读音组合
        for pronunciation in heteronym_result.split(' | '):
            results.add(pronunciation)
    
    return ' | '.join(sorted(results))

def process_name_to_pinyin_no_tone(text):
    if not text:
        return ''

    normalized_text = normalize_text_value(text, remove_name_punct=True)
    text_variants = process_text_with_numbers(normalized_text)
    results = set()
    for variant in text_variants:
        heteronym_result = to_pinyin_name_heteronym_no_tone(variant)
        for pronunciation in heteronym_result.split(' | '):
            results.add(pronunciation)
    return ' | '.join(sorted(results))

def process_text_to_pinyin(text):
    if not text:
        return ''

    text = normalize_text_value(text)
    # 按空格分割多个简称
    text_parts = [part.strip() for part in text.split(' ') if part.strip()]
    
    all_results = []
    for part in text_parts:
        text_variants = process_text_with_numbers(part)
        results = set()
        for variant in text_variants:
            # 将每个字的拼音用空格分开
            pinyin_result = ' '.join([item[0] for item in pinyin_tone3(variant)])
            results.add(pinyin_result)
        all_results.extend(sorted(results))
    
    return ' | '.join(all_results)

def process_text_to_pinyin_no_tone(text):
    if not text:
        return ''

    text = normalize_text_value(text)
    text_parts = [part.strip() for part in text.split(' ') if part.strip()]

    all_results = []
    for part in text_parts:
        text_variants = process_text_with_numbers(part)
        results = set()
        for variant in text_variants:
            pinyin_result = ' '.join([item[0] for item in pinyin_normal(variant)])
            results.add(pinyin_result)
        all_results.extend(sorted(results))

    return ' | '.join(all_results)

# 更新JSON文件
@tele_bp.route('/update_json_files', methods=['POST'])
def update_json_files():
    """更新查询模板和用户详情JSON文件"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # 生成查询模板（带音调 + 无音调）
            cursor.execute("""
                SELECT userPY, surPY, departmentPY, jobPY, unitAbbreviationPY,
                       userPY_no_tone, surPY_no_tone, departmentPY_no_tone, jobPY_no_tone, unitAbbreviationPY_no_tone
                FROM tele 
                WHERE PERSONNEL IS NOT NULL 
                AND PERSONNEL != ''
                ORDER BY NUMBER
            """)
            rows = cursor.fetchall()
            
            def expand_pinyin_variants(pinyin_str):
                if not pinyin_str:
                    return []
                variants = [variant.strip() for variant in pinyin_str.split('|')]
                return [v for v in variants if v]

            def build_templates(name_py_variants, dept_py_variants, job_py_variants, surname_py_variants, unit_abbr_py_variants, de_token):
                templates = []
                for name_py in name_py_variants:
                    for dept_py in dept_py_variants:
                        for job_py in job_py_variants:
                            templates.append(f"{{{dept_py}}}{{{name_py}}}{{{job_py}}}")
                            templates.append(f"{{{dept_py}}}{{{name_py}}}")
                            for surname_py in surname_py_variants:
                                templates.append(f"{{{dept_py}}}{{{surname_py}}}{{{job_py}}}")

                            templates.append(f"{{{dept_py}}}{{{de_token}}}{{{name_py}}}{{{job_py}}}")
                            templates.append(f"{{{dept_py}}}{{{de_token}}}{{{name_py}}}")
                            for surname_py in surname_py_variants:
                                templates.append(f"{{{dept_py}}}{{{de_token}}}{{{surname_py}}}{{{job_py}}}")

                            templates.append(f"{{{name_py}}}{{{job_py}}}")
                            for surname_py in surname_py_variants:
                                templates.append(f"{{{name_py}}}{{{surname_py}}}{{{job_py}}}")
                                templates.append(f"{{{surname_py}}}{{{job_py}}}")
                            templates.append(f"{{{name_py}}}")

                    for unit_abbr_py in unit_abbr_py_variants:
                        for job_py in job_py_variants:
                            templates.append(f"{{{unit_abbr_py}}}{{{name_py}}}{{{job_py}}}")
                            templates.append(f"{{{unit_abbr_py}}}{{{name_py}}}")
                            for surname_py in surname_py_variants:
                                templates.append(f"{{{unit_abbr_py}}}{{{surname_py}}}{{{job_py}}}")

                            templates.append(f"{{{unit_abbr_py}}}{{{de_token}}}{{{name_py}}}{{{job_py}}}")
                            templates.append(f"{{{unit_abbr_py}}}{{{de_token}}}{{{name_py}}}")
                            for surname_py in surname_py_variants:
                                templates.append(f"{{{unit_abbr_py}}}{{{de_token}}}{{{surname_py}}}{{{job_py}}}")

                        templates.append(f"{{{unit_abbr_py}}}{{{name_py}}}")
                        templates.append(f"{{{unit_abbr_py}}}{{{de_token}}}{{{name_py}}}")
                return templates

            query_templates = []
            query_templates_no_tone = []
            query_templates_no_tone = []
            query_templates_no_tone = []
            query_templates_no_tone = []

            for row in rows:
                name_py_variants = expand_pinyin_variants(row['userPY'])
                dept_py_variants = expand_pinyin_variants(row['departmentPY'])
                job_py_variants = expand_pinyin_variants(row['jobPY'])
                surname_py_variants = expand_pinyin_variants(row['surPY'])
                unit_abbr_py_variants = expand_pinyin_variants(row['unitAbbreviationPY'])

                name_py_variants_no_tone = expand_pinyin_variants(process_name_to_pinyin_no_tone(row.get('PERSONNEL', '')))
                dept_py_variants_no_tone = expand_pinyin_variants(process_text_to_pinyin_no_tone(row.get('UNIT', '')))
                job_py_variants_no_tone = expand_pinyin_variants(process_name_to_pinyin_no_tone(row.get('JOB', '')))
                surname_py_variants_no_tone = expand_pinyin_variants(process_name_to_pinyin_no_tone(row.get('surname', '')))
                unit_abbr_py_variants_no_tone = expand_pinyin_variants(process_text_to_pinyin_no_tone(row.get('unitAbbreviation', '')))

                name_py_variants_no_tone = expand_pinyin_variants(process_name_to_pinyin_no_tone(row.get('PERSONNEL', '')))
                dept_py_variants_no_tone = expand_pinyin_variants(process_text_to_pinyin_no_tone(row.get('UNIT', '')))
                job_py_variants_no_tone = expand_pinyin_variants(process_name_to_pinyin_no_tone(row.get('JOB', '')))
                surname_py_variants_no_tone = expand_pinyin_variants(process_name_to_pinyin_no_tone(row.get('surname', '')))
                unit_abbr_py_variants_no_tone = expand_pinyin_variants(process_text_to_pinyin_no_tone(row.get('unitAbbreviation', '')))

                name_py_variants_no_tone = expand_pinyin_variants(process_name_to_pinyin_no_tone(row.get('PERSONNEL', '')))
                dept_py_variants_no_tone = expand_pinyin_variants(process_text_to_pinyin_no_tone(row.get('UNIT', '')))
                job_py_variants_no_tone = expand_pinyin_variants(process_name_to_pinyin_no_tone(row.get('JOB', '')))
                surname_py_variants_no_tone = expand_pinyin_variants(process_name_to_pinyin_no_tone(row.get('surname', '')))
                unit_abbr_py_variants_no_tone = expand_pinyin_variants(process_text_to_pinyin_no_tone(row.get('unitAbbreviation', '')))

                name_py_variants_no_tone = expand_pinyin_variants(process_name_to_pinyin_no_tone(row.get('PERSONNEL', '')))
                dept_py_variants_no_tone = expand_pinyin_variants(process_text_to_pinyin_no_tone(row.get('UNIT', '')))
                job_py_variants_no_tone = expand_pinyin_variants(process_name_to_pinyin_no_tone(row.get('JOB', '')))
                surname_py_variants_no_tone = expand_pinyin_variants(process_name_to_pinyin_no_tone(row.get('surname', '')))
                unit_abbr_py_variants_no_tone = expand_pinyin_variants(process_text_to_pinyin_no_tone(row.get('unitAbbreviation', '')))

                name_py_variants_no_tone = expand_pinyin_variants(row.get('userPY_no_tone'))
                dept_py_variants_no_tone = expand_pinyin_variants(row.get('departmentPY_no_tone'))
                job_py_variants_no_tone = expand_pinyin_variants(row.get('jobPY_no_tone'))
                surname_py_variants_no_tone = expand_pinyin_variants(row.get('surPY_no_tone'))
                unit_abbr_py_variants_no_tone = expand_pinyin_variants(row.get('unitAbbreviationPY_no_tone'))

                query_templates.extend(
                    build_templates(
                        name_py_variants,
                        dept_py_variants,
                        job_py_variants,
                        surname_py_variants,
                        unit_abbr_py_variants,
                        'de5'
                    )
                )

                query_templates_no_tone.extend(
                    build_templates(
                        name_py_variants_no_tone,
                        dept_py_variants_no_tone,
                        job_py_variants_no_tone,
                        surname_py_variants_no_tone,
                        unit_abbr_py_variants_no_tone,
                        'de'
                    )
                )
            
            # 去重处理，但保持顺序
            seen = set()
            unique_templates = []
            for template in query_templates:
                if template not in seen:
                    seen.add(template)
                    unique_templates.append(template)

            seen_no_tone = set()
            unique_templates_no_tone = []
            for template in query_templates_no_tone:
                if template not in seen_no_tone:
                    seen_no_tone.add(template)
                    unique_templates_no_tone.append(template)

            seen_no_tone = set()
            unique_templates_no_tone = []
            for template in query_templates_no_tone:
                if template not in seen_no_tone:
                    seen_no_tone.add(template)
                    unique_templates_no_tone.append(template)

            seen_no_tone = set()
            unique_templates_no_tone = []
            for template in query_templates_no_tone:
                if template not in seen_no_tone:
                    seen_no_tone.add(template)
                    unique_templates_no_tone.append(template)

            seen_no_tone = set()
            unique_templates_no_tone = []
            for template in query_templates_no_tone:
                if template not in seen_no_tone:
                    seen_no_tone.add(template)
                    unique_templates_no_tone.append(template)
            
            # 写入查询模板JSON文件
            import json
            import os
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.join(current_dir, '..', '..', '..', '..')
            query_templates_file_path = os.path.join(project_root, 'asr', 'Interaction', 'data', 'query_templates.json')
            query_templates_no_tone_file_path = os.path.join(project_root, 'asr', 'Interaction', 'data', 'query_templates_no_tone.json')
            os.makedirs(os.path.dirname(query_templates_file_path), exist_ok=True)
            with open(query_templates_file_path, 'w', encoding='utf-8') as f:
                json.dump(unique_templates, f, ensure_ascii=False, indent=2)
            with open(query_templates_no_tone_file_path, 'w', encoding='utf-8') as f:
                json.dump(unique_templates_no_tone, f, ensure_ascii=False, indent=2)
            
            # 生成用户详细信息JSON
            user_details = []
            cursor.execute("""
                SELECT NUMBER, PERSONNEL, DEPARTMENT, UNIT, surname, JOB, unitAbbreviation, 
                       userPY, departmentPY, surPY, jobPY, unitAbbreviationPY, TELE_CODE, telephoneType, queryPermission
                FROM tele 
                WHERE PERSONNEL IS NOT NULL 
                AND PERSONNEL != ''
                ORDER BY NUMBER
            """)
            user_rows = cursor.fetchall()
            
            for row in user_rows:
                user_detail = {
                    "NUMBER": row['NUMBER'],
                    "PERSONNEL": row['PERSONNEL'] or '',
                    "UNIT": row['UNIT'] or '',
                    "TELE_CODE": row['TELE_CODE'] or '',
                    "JOB": row['JOB'] or '',
                    "telephoneType":row['telephoneType'] or row['DEPARTMENT'],
                    "surname": row['surname'] or '',
                    "userPY": row['userPY'] or '',
                    "surPY": row['surPY'] or '',
                    "departmentPY": row['departmentPY'] or '',
                    "jobPY": row['jobPY'] or '',
                    "unitAbbreviation": row['unitAbbreviation'] or '',
                    "unitAbbreviationPY": row['unitAbbreviationPY'] or '',
                    "queryPermission": row['queryPermission']
                }
                user_details.append(user_detail)
            
            # 写入用户详细信息JSON文件
            user_details_file_path = os.path.join(project_root, 'asr', 'Interaction', 'data', 'phone_database.json')
            os.makedirs(os.path.dirname(user_details_file_path), exist_ok=True)
            with open(user_details_file_path, 'w', encoding='utf-8') as f:
                json.dump(user_details, f, ensure_ascii=False, indent=2)
            
            return jsonify({
                'status': 200,
                'message': f'Successfully updated {len(unique_templates)} query templates and {len(user_details)} user details',
                'details': {
                    'query_templates_count': len(unique_templates),
                    'user_details_count': len(user_details)
                }
            })
            
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# 更新JSON文件中的用户权限
@tele_bp.route('/update_user_permission_in_json', methods=['POST'])
def update_user_permission_in_json():
    """更新JSON文件中的用户权限"""
    try:
        data = request.get_json()
        user_number = data.get('userNumber')
        new_permission = data.get('queryPermission')
        
        if user_number is None or new_permission is None:
            return jsonify({'status': 'error', 'message': 'Missing userNumber or queryPermission'}), 400
        
        import json
        import os
        
        # 获取文件路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.join(current_dir, '..', '..', '..', '..')
        phone_database_file_path = os.path.join(project_root, 'asr', 'Interaction', 'data', 'phone_database.json')
        
        # 读取现有的phone_database.json
        if not os.path.exists(phone_database_file_path):
            return jsonify({'status': 'error', 'message': 'phone_database.json file not found'}), 404
        
        with open(phone_database_file_path, 'r', encoding='utf-8') as f:
            user_details = json.load(f)
        
        # 找到对应的用户并更新权限
        user_found = False
        for user in user_details:
            if user['NUMBER'] == user_number:
                user['queryPermission'] = new_permission
                user_found = True
                break
        
        if not user_found:
            return jsonify({'status': 'error', 'message': f'User {user_number} not found in JSON file'}), 404
        
        # 写入更新后的文件
        with open(phone_database_file_path, 'w', encoding='utf-8') as f:
            json.dump(user_details, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            'status': 200,
            'message': f'Successfully updated user {user_number} permission to {new_permission}',
            'user_details_count': len(user_details)
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
