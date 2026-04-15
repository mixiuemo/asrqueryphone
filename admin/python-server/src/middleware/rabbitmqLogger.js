// src/middleware/rabbitmqLogger.js
const amqplib = require('amqplib');
var ini = require('ini');
var path = require('path');
var fs = require('fs');
var MQ = require('../mq')

// 构建 config.ini 文件的路径
const configFilePath = path.resolve(__dirname, '../../../../../etc/config.ini');

// 读取 config.ini 文件
const config = ini.parse(fs.readFileSync(configFilePath, 'utf-8'));

// 从 config.ini 文件中获取 RabbitMQ 服务器的配置
const MSG_SERVER_ADDR = config.MSG.MSG_SERVER_ADDR;
const MSG_SERVER_PORT = config.MSG.MSG_SERVER_PORT;
const MSG_SERVER_USER = config.MSG.MSG_SERVER_USER;
const MSG_SERVER_PASSWORD = config.MSG.MSG_SERVER_PASSWORD;

// 构造连接字符串

const connectionUrl = `amqp://${MSG_SERVER_USER}:${MSG_SERVER_PASSWORD}@${MSG_SERVER_ADDR}:${MSG_SERVER_PORT}`;
async function sendMessageToQueue(queueName, message) {
    try {
        const connection = await amqplib.connect(connectionUrl);
        const channel = await connection.createChannel();

        await channel.assertQueue(queueName, { durable: false,autoDelete:true  });

        channel.sendToQueue(queueName, Buffer.from(message));
        console.log(` [x] Sent message to queue ${queueName}: ${message}`);

        await channel.close();
        await connection.close();
    } catch (error) {
        console.error('Error sending message to RabbitMQ:', error);
    }
}

const rabbitmqLogger = (req, res, next) => {
    const startTime = Date.now();
    const method = req.method;
    const url = req.originalUrl;

    res.on('finish', () => {
        const endTime = Date.now();
        const duration = endTime - startTime;
        const status = res.statusCode;
        let message = `${method} ${url} - ${status} - ${duration}ms`;
        message = 'HEARTBEAT:' + 'PLATFORMSERVER'+`:${method} ${url} - ${status} - ${duration}ms`
        // 发送消息到 RabbitMQ
        // sendMessageToQueue('AI114', message);
        MQ.sendMessage(message)
    });

    next();
};

module.exports = rabbitmqLogger;

