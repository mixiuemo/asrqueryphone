import pymysql
import configparser
import os

def get_db_connection():
    # 读取配置文件
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), '../../../../../etc/config.ini')
    config.read(config_path, encoding='utf-8')
    
    # 从配置文件获取数据库连接信息
    db_host = config['DB']['DB_SERVER_ADDR']
    db_port = int(config['DB']['DB_SERVER_PORT'])
    db_user = config['DB']['DB_SERVER_USER']
    db_password = config['DB']['DB_SERVER_PASSWORD']
    db_name = config['DB']['DB_SERVER_DATABASE']
    
    # 创建数据库连接
    connection = pymysql.connect(
        host=db_host,
        port=db_port,
        user=db_user,
        password=db_password,
        database=db_name,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )
    
    return connection
