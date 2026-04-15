// src/config/db.js
const ini = require('ini');
const fs = require('fs');
const path = require('path');
const mysql = require('mysql2/promise');

// 构建 config.ini 文件的路径
const configFilePath = path.resolve(__dirname, '../../../../../etc/config.ini');

// 读取 config.ini 文件
const config = ini.parse(fs.readFileSync(configFilePath, 'utf-8'));

// 从 config.ini 文件中获取数据库配置
const DB_SERVER_ADDR = config.DB.DB_SERVER_ADDR;
const DB_USER = 'root'; // 替换为你的数据库用户名
const DB_PASSWORD = 'mysql'; // 替换为你的数据库密码
const DB_NAME = 'rgt'; // 替换为你的数据库名称

// 创建 MySQL 数据库连接池
const pool = mysql.createPool({
  host: DB_SERVER_ADDR,
  user: DB_USER,
  password: DB_PASSWORD,
  database: DB_NAME,
  waitForConnections: true,
  connectionLimit: 10,
  queueLimit: 0
});

module.exports = pool;