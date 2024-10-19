# app.py

from flask import Flask, request, redirect, url_for, send_from_directory, render_template
import os

app = Flask(__name__)

# 设置上传文件夹
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
        if file and allowed_file(file.filename):
            filename = file.filename
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('upload_file'))

    # 显示上传表单和文件列表
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    return render_template('upload.html', files=files)

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

if __name__ == '__main__':
    app.run(debug=True)