// server/config/config.js
const fs = require('fs');
const path = require('path');

// 加载配置文件
const configPath = path.resolve(__dirname, 'config.json');
console.log(`配置文件路径: ${configPath}`); // 打印配置文件路径

try {
    const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
    // console.log('配置文件内容:', config); // 打印配置文件内容
    global.config = config;

    // 如果你需要直接访问 global.TTS，应该这样写：
    // console.log('配置文件内容:', global.config); // 打印配置文件内容
    module.exports = config;
} catch (error) {
    console.error('加载配置文件时出错:', error);
    // 这里可以根据需要抛出错误或设置默认配置
    // throw;
 error}