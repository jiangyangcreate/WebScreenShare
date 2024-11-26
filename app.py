from flask import Flask, request, redirect, url_for, send_from_directory, render_template, jsonify
from flask_socketio import SocketIO, emit
import os
from datetime import datetime
import secrets
from flask_cors import CORS

# 生成一个随机的密钥
secret_key = secrets.token_hex(16)  # 生成 32 个字符的随机字符串
app = Flask(__name__)
CORS(app)  # 允许所有域名的跨域请求
app.config['SECRET_KEY'] = secret_key  # 使用生成的密钥
socketio = SocketIO(app, max_http_buffer_size=200 * 1024 ** 2)

# 设置上传文件夹
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # 检查是否有文件上传
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            return redirect(request.url)
        if file:
            filename = file.filename
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('upload_file'))

    # 显示上传表单和文件列表
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    return render_template('upload.html', files=files)

@app.route('/upload_video', methods=['POST'])
def upload_video():
    if 'video' not in request.files:
        return jsonify({'status': 'fail', 'message': 'No video part'}), 400
    video = request.files['video']
    if video.filename == '':
        return jsonify({'status': 'fail', 'message': 'No selected video'}), 400
    if video:
        # 自动生成文件名为当前日期+时间（精确到毫秒）
        now = datetime.now()
        filename = now.strftime("%Y-%m-%d_%H-%M-%S_%f")[:-3] + ".mp4"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        video.save(filepath)
        return jsonify({'status': 'success', 'filename': filename}), 200
    else:
        return jsonify({'status': 'fail', 'message': 'File type not allowed'}), 400

@app.route('/uploads/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# 新增的路由：设备选择页面
@app.route('/media_selection')
def media_selection():
    return render_template('media_selection.html')

# 新增的路由：媒体接口页面
@app.route('/media_interface')
def media_interface():
    # 获取用户选择的参数
    screen = request.args.get('screen') == 'on'
    camera = request.args.get('camera') == 'on'
    sound = request.args.get('sound') == 'on'

    # 至少选择一项已经在前端验证，这里不再重复
    return render_template('media_interface.html', screen=screen, camera=camera, sound=sound)

# 新增的路由：媒体查看页面
@app.route('/media_view')
def media_view():
    return render_template('media_view.html')

# SocketIO 事件处理
host_sid = None

@socketio.on('connect', namespace='/host')
def host_connect():
    global host_sid
    host_sid = request.sid

@socketio.on('disconnect', namespace='/host')
def host_disconnect():
    global host_sid
    host_sid = None
    socketio.emit('sharing_status', {'sharing': False}, namespace='/viewer')

@socketio.on('sharing_status', namespace='/host')
def sharing_status(status):
    socketio.emit('sharing_status', status, namespace='/viewer')

@socketio.on('viewer-join', namespace='/viewer')
def viewer_join(viewer_id):
    if host_sid:
        socketio.emit('viewer-join', request.sid, room=host_sid, namespace='/host')
    else:
        emit('sharing_status', {'sharing': False})

@socketio.on('offer', namespace='/host')
def handle_offer(data):
    to = data['to']
    offer = data['offer']
    socketio.emit('offer', {'from': request.sid, 'offer': offer}, room=to, namespace='/viewer')

@socketio.on('answer', namespace='/viewer')
def handle_answer(data):
    to = data['to']
    answer = data['answer']
    socketio.emit('answer', {'from': request.sid, 'answer': answer}, room=to, namespace='/host')

@socketio.on('candidate', namespace='/host')
def host_candidate(data):
    to = data['to']
    candidate = data['candidate']
    socketio.emit('candidate', {'from': request.sid, 'candidate': candidate}, room=to, namespace='/viewer')

@socketio.on('candidate', namespace='/viewer')
def viewer_candidate(data):
    to = data['to']
    candidate = data['candidate']
    socketio.emit('candidate', {'from': request.sid, 'candidate': candidate}, room=to, namespace='/host')

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=8080)
