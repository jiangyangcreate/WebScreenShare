// static/js/deviceDetection.js

// 检测摄像头是否存在
function hasCamera() {
    return navigator.mediaDevices.enumerateDevices()
        .then(devices => {
            return devices.some(device => device.kind === 'videoinput');
        })
        .catch(err => {
            console.error('Error detecting camera:', err);
            return false;
        });
}

// 检测麦克风是否存在
function hasMicrophone() {
    return navigator.mediaDevices.enumerateDevices()
        .then(devices => {
            return devices.some(device => device.kind === 'audioinput');
        })
        .catch(err => {
            console.error('Error detecting microphone:', err);
            return false;
        });
}

// 显示检测结果
function displayDeviceStatus() {
    hasCamera().then(camera => {
        const cameraStatus = document.getElementById('camera-status');
        if (camera) {
            cameraStatus.textContent = '摄像头: 已连接';
            cameraStatus.style.color = 'green';
        } else {
            cameraStatus.textContent = '摄像头: 未连接';
            cameraStatus.style.color = 'red';
        }
    });

    hasMicrophone().then(microphone => {
        const microphoneStatus = document.getElementById('microphone-status');
        if (microphone) {
            microphoneStatus.textContent = '麦克风: 已连接';
            microphoneStatus.style.color = 'green';
        } else {
            microphoneStatus.textContent = '麦克风: 未连接';
            microphoneStatus.style.color = 'red';
        }
    });
}

// 当页面加载完成后执行
window.addEventListener('load', displayDeviceStatus);

function detectDevices() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) {
        console.log('浏览器不支持设备检测');
        return;
    }

    navigator.mediaDevices.enumerateDevices()
        .then(function(devices) {
            let hasCamera = false;
            let hasMicrophone = false;

            devices.forEach(function(device) {
                if (device.kind === 'videoinput') {
                    hasCamera = true;
                }
                if (device.kind === 'audioinput') {
                    hasMicrophone = true;
                }
            });

            const cameraCheckbox = document.getElementById('camera-checkbox');
            const soundCheckbox = document.getElementById('sound-checkbox');

            if (hasCamera) {
                cameraCheckbox.disabled = false;
            } else {
                cameraCheckbox.disabled = true;
                cameraCheckbox.checked = false;
            }

            if (hasMicrophone) {
                soundCheckbox.disabled = false;
            } else {
                soundCheckbox.disabled = true;
                soundCheckbox.checked = false;
            }
        })
        .catch(function(err) {
            console.error('设备检测时出错:', err);
        });
}

// 当页面内容加载完毕后执行设备检测
document.addEventListener('DOMContentLoaded', detectDevices);
