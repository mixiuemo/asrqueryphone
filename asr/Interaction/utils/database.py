import re
from mysql.connector import pooling
from mysql.connector import Error
from datetime import datetime, timezone, timedelta
from pypinyin import pinyin, Style
from utils.loggeruitls import Logger
import time
import os
import configparser
import mysql.connector

log = Logger()

# 读取配置文件
config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../etc/config.ini'))
config = configparser.ConfigParser()
config.read(config_path, encoding='utf-8')

# 从配置文件获取数据库配置
dbconfig = {
    "host": config.get('DB', 'DB_SERVER_ADDR'),
    "port": int(config.get('DB', 'DB_SERVER_PORT')),
    "user": config.get('DB', 'DB_SERVER_USER'),
    "password": config.get('DB', 'DB_SERVER_PASSWORD'),
    "database": config.get('DB', 'DB_SERVER_DATABASE'),
    "connection_timeout": 10, 
    "autocommit": True, 
    "charset": "utf8mb4",
    "use_unicode": True,
}

connection_pool = pooling.MySQLConnectionPool(
    pool_name="mypool",
    pool_size=32, 
    pool_reset_session=True, 
    **dbconfig
)

def connect_to_mysql():
    connection = None
    try:
        connection = connection_pool.get_connection()
        if connection.is_connected():
            log.info("成功连接到MySQL数据库")
            return connection
        else:
            log.error("获取到的连接无效")
            if connection:
                connection.close()
            return None
    except Error as e:
        log.error(f"连接MySQL数据库时出错: {e}")
        if connection:
            try:
                connection.close()
            except:
                pass
        return None
    except Exception as e:
        log.error(f"连接MySQL数据库时发生未知错误: {e}")
        if connection:
            try:
                connection.close()
            except:
                pass
        return None

def safe_close_connection(connection):
    if connection:
        try:
            if connection.is_connected():
                connection.close()
                log.info("数据库连接已安全关闭")
        except Exception as e:
            log.error(f"关闭数据库连接时发生错误: {e}")

def safe_close_cursor(cursor):
    if cursor:
        try:
            cursor.close()
        except Exception as e:
            log.error(f"关闭游标时发生错误: {e}")


def insert_into_database(userResult, sysResult, wavFileName, syswavFileName, channelNumber, callerNumber, callpersonnel, calljob, callunit):
    current_timestamp = int(time.time())
    userResult = userResult.replace(" ", "")
    db_connection = connect_to_mysql()
    if db_connection is None:
        return False
    try:
        with db_connection.cursor() as cursor:
            sql = """
            INSERT INTO ai114_result (userResult, sysResult, wavFileName, syswavFileName, resultTime114, channelNumber, callerNumber, callPersonnel, callJob, callUnit)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """
            cursor.execute(sql, (userResult, sysResult, wavFileName, syswavFileName, current_timestamp, channelNumber, callerNumber, callpersonnel, calljob, callunit))
        log.info("通道号为: %s 数据已成功插入数据库。", channelNumber)
        return True
    except Exception as e:
        log.error(f"通道号为: %s 插入数据库时发生错误: %s", channelNumber, e)
        return False
    finally:
        safe_close_connection(db_connection)


def get_connection():
    """获取数据库连接"""
    try:
        conn = mysql.connector.connect(**dbconfig)
        return conn
    except Exception as e:
        print(f"数据库连接失败: {e}")
        return None

def load_system_config():
    enable_transfer = False
    enable_manual = False
    
    try:
        connection = connect_to_mysql()
        if connection:
            try:
                cursor = connection.cursor(dictionary=True)
                
                # 检查表是否存在
                cursor.execute("SHOW TABLES LIKE 'ai114_config'")
                if not cursor.fetchone():
                    log.info("ai114_config表不存在，使用默认配置")
                    return enable_transfer, enable_manual
                
                # 读取转接配置
                cursor.execute("SELECT value FROM ai114_config WHERE name = 'ai114_zj' LIMIT 1")
                result = cursor.fetchone()
                if result and result['value'] is not None:
                    enable_transfer = bool(int(result['value']))
                    log.info(f"从数据库读取转接配置: {enable_transfer}")
                else:
                    log.info("未找到转接配置，使用默认值: False")
                
                # 读取转人工配置
                cursor.execute("SELECT value FROM ai114_config WHERE name = 'ai114_zrg' LIMIT 1")
                result = cursor.fetchone()
                if result and result['value'] is not None:
                    enable_manual = bool(int(result['value']))
                    log.info(f"从数据库读取转人工配置: {enable_manual}")
                else:
                    log.info("未找到转人工配置，使用默认值: False")
                
                cursor.close()
                log.info(f"配置加载完成 - 转接: {enable_transfer}, 转人工: {enable_manual}")
                
            except Exception as e:
                log.error(f"读取配置时发生错误: {e}")
            finally:
                safe_close_connection(connection)
        else:
            log.warning("无法连接到数据库，使用默认配置")
    except Exception as e:
        log.error(f"配置加载失败: {e}")
    
    return enable_transfer, enable_manual

