// server/config/config.js
const fs = require('fs');
const path = require('path');

// 加载配置文件
const config = JSON.parse(
    fs.readFileSync(path.resolve(__dirname, 'config.json'), 'utf8')
);

// 将配置挂载到 global 对象
global.config = config;

// 导出配置
module.exports = config;