let serverIP = window.location.hostname;
if (process.env.NODE_ENV === 'development') {
    serverIP = 'localhost'
}
var serverPORT = 5000;
global.serverPORT = serverPORT;
var ttsServerHost = 'http://127.0.0.1:8333';

export default {
    title: '新殿光智能查号接转平台',
    version: "1.3.6",
    /**
     * @description api请求基础路径
     */
    baseUrl: {
        dev: 'http://' + serverIP + ':' + serverPORT + '/api',
        pro: 'http://' + serverIP + ':' + serverPORT + '/api',
    },
    baseFileUrl: {
        dev: 'http://' + serverIP + ':' + serverPORT + '/file/',
        pro: 'http://' + serverIP + ':' + serverPORT + '/file/',
    },
    baseMediaUrl: {
        dev: 'http://' + serverIP + ':' + serverPORT + '/api/vi/media/',
        pro: 'http://' + serverIP + ':' + serverPORT + '/api/vi/media/',
    },
    ttsBaseUrl: {
        dev: ttsServerHost + '/tts/audio/',
        pro: ttsServerHost + '/tts/audio/',
    },
    serverIP: serverIP
}
