const amqp = require('amqplib');
var ini = require('ini');
var path = require('path');
var fs = require('fs');
const mysql = require('mysql2/promise');
var conn;
var ExchangeName = 'AI114'
const configFilePath = path.resolve(__dirname, '../../../../etc/config.ini');
const config = ini.parse(fs.readFileSync(configFilePath, 'utf-8'));

// 从 config.ini 文件中获取 RabbitMQ 服务器的配置
const MSG_SERVER_ADDR = config.MSG.MSG_SERVER_ADDR;
const MSG_SERVER_PORT = config.MSG.MSG_SERVER_PORT;
const MSG_SERVER_USER = config.MSG.MSG_SERVER_USER;
const MSG_SERVER_PASSWORD = config.MSG.MSG_SERVER_PASSWORD;

// 创建 MySQL 数据库连接池
const pool = mysql.createPool({
    host: config.DB.DB_SERVER_ADDR,
    user: 'root', // 替换为你的数据库用户名
    password: 'mysql', // 替换为你的数据库密码
    database: 'rgt', // 替换为你的数据库名称
    waitForConnections: true,
    connectionLimit: 10,
    queueLimit: 0
  });

let MQ = {
    connect: async function () {
        try {
            const connectionUrl = `amqp://${MSG_SERVER_USER}:${MSG_SERVER_PASSWORD}@${MSG_SERVER_ADDR}:${MSG_SERVER_PORT}`;

            // 连接到 RabbitMQ 服务器
            const conn = await amqp.connect(connectionUrl);
            console.log('Connected to RabbitMQ');
            
            // 创建通道
            var channel = await conn.createChannel();
            console.log('Channel created');

            await channel.assertExchange(ExchangeName, 'fanout', { durable: false }); // 声明一个持久的direct交换机 // 声明交换机

            console.log('declareExchange:');
            var result = await channel.assertQueue('NODEJS-QUEUE', { durable: false,autoDelete:true,autoAck:true }); // 声明一个持久的队列
            console.log('Queue declared:', result.queue);
            await channel.bindQueue(result.queue, ExchangeName, ''); // 将队列绑定到交换机，并指定路由键
            
            channel.consume(result.queue, async function(msg) {
              console.log(" [x] Received %s", msg.content.toString());
              if (msg !== null) {
                    // 解析消息内容
                    const messageContent = msg.content.toString();
                    const messageParts = messageContent.split(':');
                    if(messageParts[0] == 'HEARTBEAT'){
                        const service = messageParts[1].trim(); // 提取服务类型
                        const status = 1; // 状态固定为 1
                        const updateTime = new Date(); // 当前时间
            
                        // 使用 INSERT ... ON DUPLICATE KEY UPDATE 语法
                        await pool.execute(
                            'INSERT INTO ai114_serverSet (service, status, update_time) VALUES (?, ?, ?) ON DUPLICATE KEY UPDATE status = VALUES(status), update_time = VALUES(update_time)',
                            [service, status, updateTime]
                        );
                    }
            }
            }, {
                noAck: true
            });
            
            return { conn, channel };
        } catch (error) {
            console.error('Failed to connect to RabbitMQ', error);
        }
    },
    close: async function () {
        try {
            if (MQ.channel) {
                await MQ.channel.close();
                console.log('Channel closed');
            }
        } catch (error) {
            console.error('Failed to close channel', error);
        }
    },
    sendMessage: async function (message) {
        try {
            if(!MQ.chnnel){
                const { conn, channel } = await MQ.connect();
                MQ.channel =  channel;
            }

            MQ.channel.publish(ExchangeName, '', Buffer.from(message));
            console.log(` [x] Sent: ${message}`);

            // 确保在完成后关闭连接和通道
        } catch (error) {
            console.error('Failed to send message', error);
        }
    }
}
module.exports = MQ;
