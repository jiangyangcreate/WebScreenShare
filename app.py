from flask import Flask, render_template, request, send_from_directory, abort, Response, stream_with_context
import os
import time
import cv2
import numpy as np
from PIL import ImageGrab
import threading
from greenlet import getcurrent as get_ident
import pyaudio
import logging

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# 设置上传文件夹
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# 添加下载文件的路由
@app.route("/download/<filename>")
def download_file(filename):
    try:
        return send_from_directory(
            app.config["UPLOAD_FOLDER"], filename, as_attachment=True
        )
    except FileNotFoundError:
        abort(404)

@app.route("/", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        if "file" not in request.files:
            return "没有文件部分"
        file = request.files["file"]
        if file.filename == "":
            return "没有选择文件"
        if file:
            filename = file.filename
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            return "文件上传成功"
    return render_template("upload.html")

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

class Audio:
    def __init__(self):
        # Audio configuration
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 2
        self.RATE = 16000
        self.CHUNK = 1024
        self.BITS_PER_SAMPLE = 16
        
        # Initialize PyAudio
        self.audio = pyaudio.PyAudio()
        self.first_run = True
        self.wav_header = self.generate_header(self.RATE, self.BITS_PER_SAMPLE, self.CHANNELS)
        
        # Open audio stream
        self.stream = self.audio.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            input_device_index=1,
            frames_per_buffer=self.CHUNK,
        )
        self.get_audio = self._get_audio_first_time

    def generate_header(self, sample_rate, bits_per_sample, channels):
        # Generate WAV header
        datasize = 2000 * 10**6
        o = bytes("RIFF", "ascii")
        o += (datasize + 36).to_bytes(4, "little")
        o += bytes("WAVE", "ascii")
        o += bytes("fmt ", "ascii")
        o += (16).to_bytes(4, "little")
        o += (1).to_bytes(2, "little")
        o += (channels).to_bytes(2, "little")
        o += (sample_rate).to_bytes(4, "little")
        o += (sample_rate * channels * bits_per_sample // 8).to_bytes(4, "little")
        o += (channels * bits_per_sample // 8).to_bytes(2, "little")
        o += (bits_per_sample).to_bytes(2, "little")
        o += bytes("data", "ascii")
        o += (datasize).to_bytes(4, "little")
        return o

    def _get_audio_first_time(self):
        # Get audio data for the first time (including WAV header)
        data = self.stream.read(self.CHUNK)
        self.get_audio = self._get_audio_subsequent_times  # Switch method for subsequent calls
        return self.wav_header + data

    def _get_audio_subsequent_times(self):
        # Get audio data for subsequent times
        if self.stream:
            return self.stream.read(self.CHUNK)
        else:
            return b'\x00' * self.CHUNK * 2  # Return silent data if stream is closed

class CameraEvent(object):
    def __init__(self):
        self.events = {}
        self.lock = threading.Lock()

    def wait(self):
        ident = get_ident()
        with self.lock:
            if ident not in self.events:
                self.events[ident] = [threading.Event(), time.time()]
            event = self.events[ident][0]
        event.wait()

    def set(self):
        now = time.time()
        with self.lock:
            remove = []
            for ident, event in self.events.items():
                if not event[0].is_set():
                    event[0].set()
                    event[1] = now
                else:
                    if now - event[1] > 5:
                        remove.append(ident)
            for ident in remove:
                del self.events[ident]

    def clear(self):
        ident = get_ident()
        with self.lock:
            if ident in self.events:
                self.events[ident][0].clear()

class BaseCamera(object):
    def __init__(self):
        self.thread = None
        self.frame = None
        self.last_access = 0
        self.event = CameraEvent()
        if self.thread is None:
            self.last_access = time.time()
            self.thread = threading.Thread(target=self._thread)
            self.thread.start()
            while self.get_frame() is None:
                time.sleep(0)

    def get_frame(self):
        self.last_access = time.time()
        self.event.wait()
        self.event.clear()
        return self.frame

    @staticmethod
    def frames():
        raise RuntimeError("must be implemented by subclass")

    def _thread(self):
        print("Starting camera thread.")
        try:
            frames_iterator = self.frames()
            for frame in frames_iterator:
                self.frame = frame
                self.event.set()
                time.sleep(0)
                if time.time() - self.last_access > 10:
                    frames_iterator.close()
                    print("Camera thread stopped due to inactivity.")
                    break
        except Exception as e:
            print(f"Camera thread encountered an error: {e}")
        finally:
            self.thread = None
            self.release_resources()

    def release_resources(self):
        pass

class Camera(BaseCamera):
    def __init__(self):
        self.cap = None
        super().__init__()

    def frames(self):
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            raise RuntimeError("can't open camera")
        while True:
            success, frame_camera = self.cap.read()
            if not success:
                logging.error("can't read frame from camera")
                break
            else:
                ret, jpeg_camera = cv2.imencode('.jpg', frame_camera)
                if not ret:
                    logging.error("can't encode image")
                    continue
                yield jpeg_camera.tobytes()

    def release_resources(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None
            logging.info("camera resources released")

class DesktopCapture(BaseCamera):
    def frames(self):
        while True:
            screen = np.array(ImageGrab.grab())
            frame = cv2.cvtColor(screen, cv2.COLOR_RGB2BGR)
            ret, jpeg = cv2.imencode('.jpg', frame)
            if not ret:
                logging.error("can't encode desktop image")
                continue
            yield jpeg.tobytes()

def gen_video(camera):
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

def gen_audio(audio):
    while True:
        data = audio.get_audio()
        yield data

@app.route("/camera_video")
def camera_video_feed():
    return Response(gen_video(Camera()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route("/desk_video")
def desktop_video_feed():
    return Response(gen_video(DesktopCapture()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route("/audio_feed")
def audio_feed():
    return Response(stream_with_context(gen_audio(Audio())))

@app.route("/c")
def camera_page():
    return render_template("stream.html", video_url="/camera_video", audio_url="/audio_feed")

@app.route("/d")
def desktop_page():
    return render_template("stream.html", video_url="/desk_video", audio_url="/audio_feed")

if __name__ == "__main__":
    try:
        # Ensure upload folder exists
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        
        # Server configuration
        HOST = "0.0.0.0"  # Use this to make the server accessible from other devices on the network
        PORT = 8001
        
        # Run the Flask app
        app.run(threaded=True, host=HOST, port=PORT, debug=True)
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        # You may choose to keep the program running here
