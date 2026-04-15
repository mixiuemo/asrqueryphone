from flask import Blueprint, request, jsonify, Response, stream_with_context
import threading
import time
import json
import queue
import uuid
import os
import sys

COMMON_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../common'))
if COMMON_PATH not in sys.path:
    sys.path.append(COMMON_PATH)

from rabbitmq import RabbitMQ

mqtest_bp = Blueprint('mqtest', __name__)

MQ_publisher = None

CLIENTS = {}
CLIENTS_LOCK = threading.Lock()
SEQ_TO_CLIENT = {}
SEQ_LOCK = threading.Lock()


def set_MQ(mq):
    global MQ_publisher
    MQ_publisher = mq


def _register_client(client_id):
    q = queue.Queue()
    with CLIENTS_LOCK:
        CLIENTS[client_id] = q
    return q


def _remove_client(client_id):
    with CLIENTS_LOCK:
        CLIENTS.pop(client_id, None)


def _push_to_client(client_id, payload):
    with CLIENTS_LOCK:
        q = CLIENTS.get(client_id)
    if q:
        q.put(payload)
        return True
    return False


def _broadcast(payload):
    with CLIENTS_LOCK:
        queues = list(CLIENTS.values())
    for q in queues:
        q.put(payload)


def _parse_kv_message(message):
    parts = message.split(':')
    if not parts:
        return None
    data = {}
    for part in parts[1:]:
        if '=' in part:
            k, v = part.split('=', 1)
            data[k] = v
    return data


def _handle_inte_msg(message):
    data = _parse_kv_message(message) or {}
    seq = data.get('SEQ')
    payload = {
        "type": "inte_msg",
        "seq": seq,
        "text": data.get('TEXT', ''),
        "file": data.get('FILE', ''),
        "channel": data.get('CHANNEL', ''),
        "phone": data.get('PHONE', ''),
        "switch": data.get('SWITCH', ''),
        "caller": data.get('CALLER', ''),
        "call_name": data.get('CALL_NAME', ''),
        "call_job": data.get('CALL_JOB', ''),
        "call_unit": data.get('CALL_UNIT', ''),
        "result_unit": data.get('RESULT_UNIT', ''),
        "result_name": data.get('RESULT_NAME', ''),
        "result_job": data.get('RESULT_JOB', ''),
        "raw": message,
    }

    target_client = None
    if seq:
        with SEQ_LOCK:
            target_client = SEQ_TO_CLIENT.pop(seq, None)

    if target_client:
        if not _push_to_client(target_client, payload):
            _broadcast(payload)
    else:
        _broadcast(payload)


def _mqtest_callback(ch, method, properties, body):
    try:
        message = body.decode('utf-8')
    except Exception:
        return

    if message.startswith("INTE_MSG"):
        _handle_inte_msg(message)
    elif message.startswith("ASR_MSG"):
        data = _parse_kv_message(message) or {}
        seq = data.get('SEQ')
        payload = {
            "type": "asr_result",
            "seq": seq,
            "channel": data.get('CHANNEL', ''),
            "asr_content": data.get('ASRCONTENT', ''),
            "raw": message,
        }
        target_client = None
        if seq:
            with SEQ_LOCK:
                target_client = SEQ_TO_CLIENT.pop(seq, None)
        if target_client:
            if not _push_to_client(target_client, payload):
                _broadcast(payload)
        else:
            _broadcast(payload)
    elif message.startswith("AI114_TTS_RESULT"):
        data = _parse_kv_message(message) or {}
        seq = data.get('SEQ')
        payload = {
            "type": "tts_result",
            "seq": seq,
            "channel": data.get('CHANNEL', ''),
            "phone": data.get('PHONE', ''),
            "switch": data.get('SWITCH', ''),
            "file": data.get('FILE', ''),
            "prompt_file": data.get('PROMPT_FILE', ''),
            "raw": message,
        }
        target_client = None
        if seq:
            with SEQ_LOCK:
                target_client = SEQ_TO_CLIENT.pop(seq, None)
        if target_client:
            if not _push_to_client(target_client, payload):
                _broadcast(payload)
        else:
            _broadcast(payload)


def _mqtest_loop():
    while True:
        try:
            mq_listener = RabbitMQ()
            mq_listener.connect()
            mq_listener.consume(_mqtest_callback)
        except Exception:
            time.sleep(5)


def start_mqtest_listener():
    threading.Thread(target=_mqtest_loop, daemon=True).start()


@mqtest_bp.route('/send', methods=['POST'])
def send_mq_test():
    data = request.get_json(silent=True) or {}
    text = (data.get('text') or '').strip()
    client_id = (data.get('clientId') or '').strip()

    if not text:
        return jsonify({"error": "text required"}), 400

    if MQ_publisher is None:
        return jsonify({"error": "MQ not ready"}), 500

    seq = data.get('seq') or str(uuid.uuid4())[:8]
    channel = 99
    phone = "13800138000"
    user_circuit = "10081"
    filename = f"test_{int(time.time())}.wav"

    message = (
        f"ASR_MSG:"
        f"CHANNEL={channel}:"
        f"SEQ={seq}:"
        f"FILE={filename}:"
        f"UNIT=:"
        f"PERSONNEL=:"
        f"SURNAME=:"
        f"POST=:"
        f"PHONE={phone}:"
        f"ASRCONTENT={text}:"
        f"USERCIRCUIT={user_circuit}"
    )

    ok = MQ_publisher.publish(message)
    if not ok:
        return jsonify({"error": "publish failed"}), 500

    if client_id:
        with SEQ_LOCK:
            SEQ_TO_CLIENT[seq] = client_id

    return jsonify({
        "seq": seq,
        "channel": channel,
        "message": message
    })


@mqtest_bp.route('/send_record', methods=['POST'])
def send_mq_test_record():
    data = request.get_json(silent=True) or {}
    audio_b64 = (data.get('audio_b64') or '').strip()
    client_id = (data.get('clientId') or '').strip()

    if not audio_b64:
        return jsonify({"error": "audio_b64 required"}), 400

    if MQ_publisher is None:
        return jsonify({"error": "MQ not ready"}), 500

    seq = data.get('seq') or str(uuid.uuid4())[:8]
    channel = 99
    phone = "13800138000"
    user_circuit = "10081"

    message = (
        f"RECORD:"
        f"CHANNEL={channel}:"
        f"USERCIRCUIT={user_circuit}:"
        f"SEQ={seq}:"
        f"FILE={audio_b64}:"
        f"PHONE={phone}"
    )

    ok = MQ_publisher.publish(message)
    if not ok:
        return jsonify({"error": "publish failed"}), 500

    if client_id:
        with SEQ_LOCK:
            SEQ_TO_CLIENT[seq] = client_id

    return jsonify({
        "seq": seq,
        "channel": channel,
        "message": message
    })


@mqtest_bp.route('/send_tts', methods=['POST'])
def send_mq_test_tts():
    data = request.get_json(silent=True) or {}
    text = (data.get('text') or '').strip()
    client_id = (data.get('clientId') or '').strip()

    if not text:
        return jsonify({"error": "text required"}), 400

    if MQ_publisher is None:
        return jsonify({"error": "MQ not ready"}), 500

    seq = data.get('seq') or str(uuid.uuid4())[:8]
    channel = 99
    prompt_name = f"prompt_{channel}_{int(time.time() * 1000)}.wav"
    message = (
        f"INTE_MSG:"
        f"SEQ={seq}:"
        f"TEXT={text}:"
        f"FILE={prompt_name}:"
        f"CHANNEL={channel}:"
        f"PHONE=:"
        f"SWITCH=0:"
        f"CALLER=13800138000:"
        f"CALL_NAME=张三:"
        f"CALL_JOB=工程师:"
        f"CALL_UNIT=技术部:"
        f"RESULT_UNIT=:"
        f"RESULT_NAME=:"
        f"RESULT_JOB=:"
    )

    ok = MQ_publisher.publish(message)
    if not ok:
        return jsonify({"error": "publish failed"}), 500

    if client_id:
        with SEQ_LOCK:
            SEQ_TO_CLIENT[seq] = client_id

    return jsonify({
        "seq": seq,
        "channel": channel,
        "message": message
    })


@mqtest_bp.route('/stream', methods=['GET'])
def stream_mq_test():
    client_id = (request.args.get('clientId') or '').strip()
    if not client_id:
        return jsonify({"error": "clientId required"}), 400

    q = _register_client(client_id)

    def event_stream():
        try:
            yield f"event: open\ndata: {json.dumps({'type': 'open', 'clientId': client_id})}\n\n"
            last_ping = time.time()
            while True:
                try:
                    payload = q.get(timeout=1)
                    data = json.dumps(payload, ensure_ascii=False)
                    yield f"data: {data}\n\n"
                except queue.Empty:
                    if time.time() - last_ping > 20:
                        yield "event: ping\ndata: {}\n\n"
                        last_ping = time.time()
        finally:
            _remove_client(client_id)

    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no"
    }
    return Response(stream_with_context(event_stream()), mimetype='text/event-stream', headers=headers)
