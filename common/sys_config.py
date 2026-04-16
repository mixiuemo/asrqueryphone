import os
import configparser

config = configparser.ConfigParser()
class SysConfig:
    def __init__(self,path='../../../etc/config.ini'):
        
        try:
            stamp = os.stat(path).st_mtime
        except FileNotFoundError:
            path='../../etc/config.ini'
        
        try:
            stamp = os.stat(path).st_mtime
        except FileNotFoundError:
            path='../etc/config.ini'

        try:
            stamp = os.stat(path).st_mtime
        except FileNotFoundError:
            path='../../../../etc/config.ini'

        config.read(path, encoding='utf-8')

    def get(self, sect, item):
        """读取配置；raw=True 避免插值阶段对非字符串值报错；兼容列表等异常写入。"""
        try:
            v = config.get(sect, item, fallback='', raw=True)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return ''
        if v is None:
            return ''
        if isinstance(v, (list, tuple)):
            v = v[0] if len(v) > 0 else ''
        if not isinstance(v, str):
            v = str(v)
        return v