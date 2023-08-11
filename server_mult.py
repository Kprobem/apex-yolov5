import pickle
import socket
import sys
import threading
import time
import traceback

import cv2
import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from apex_yolov5 import LogUtil
from apex_yolov5.LogWindow import LogWindow
from apex_yolov5.socket import socket_util, yolov5_handler, log_ui
from apex_yolov5.socket.config import global_config

server_socket_list = []


class ServerSocket:

    def __init__(self):
        self.log_util = LogUtil.LogUtil()

    def start(self, listener_ip, listener_port):
        # 创建一个TCP/IP套接字
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # 绑定服务器地址和端口
        server_address = (listener_ip, listener_port)
        server_socket.bind(server_address)
        # 监听客户端连接
        server_socket.listen(1)
        buffer_size = global_config.buffer_size
        while True:
            total_size = 0
            LogWindow().print_log('等待客户端连接...')
            # 等待客户端连接
            client_socket, client_address = server_socket.accept()
            LogWindow().print_log('客户端已连接:{}'.format(client_address))
            try:
                print_count = 0
                compute_time = time.time()
                while True:
                    t0 = time.time()
                    # 接收客户端发送的图像数据
                    t1 = time.time()
                    img_data = socket_util.recv(client_socket, buffer_size=buffer_size)
                    self.log_util.set_time(str(listener_port) + ":接受图片", time.time() - t1)
                    t5 = time.time()
                    # img_data = zlib.decompress(img_data)
                    self.log_util.set_time("解压图片", time.time() - t5)
                    t2 = time.time()
                    total_size += len(img_data)
                    # 将接收到的数据转换为图像
                    img0 = np.frombuffer(img_data, dtype='uint8')
                    img0 = img0.reshape((global_config.monitor["height"], global_config.monitor["width"], 3))
                    img0 = cv2.cvtColor(img0, cv2.COLOR_BGRA2BGR)
                    self.log_util.set_time(str(listener_port) + ":转换图片", time.time() - t2)
                    # 在这里可以对图像进行进一步处理
                    t3 = time.time()
                    aims = yolov5_handler.get_aims(img0)
                    self.log_util.set_time(str(listener_port) + ":转换坐标", time.time() - t3)
                    t4 = time.time()
                    aims_data = pickle.dumps(aims)
                    socket_util.send(client_socket, aims_data, buffer_size=buffer_size)
                    self.log_util.set_time(str(listener_port) + ":发送坐标", time.time() - t4)
                    if global_config.is_show_debug_window:
                        log_ui.show(aims, img0)
                    print_count += 1
                    now = time.time()
                    if now - compute_time > 1:
                        LogWindow().print_log(
                            "识别[{}]次，传输{:.1f}M/s".format(print_count, (1.0 * total_size / 1024 / 1024)))
                        self.log_util.print_time(print_count)
                        total_size = 0
                        print_count = 0
                        compute_time = now
            except Exception as e:
                print(e)
                traceback.print_exc()
                pass
            finally:
                # 关闭连接
                try:
                    client_socket.close()
                except:
                    pass
                log_ui.destroy()


# main()
if __name__ == "__main__":
    app = QApplication(sys.argv)
    log_window = LogWindow()
    if global_config.is_show_debug_window:
        log_window.setWindowFlags(Qt.WindowStaysOnTopHint)
        log_window.show()

    listener_ports = global_config.listener_ports
    for listener_port in listener_ports:
        server_socket = ServerSocket()
        server_socket_list.append(server_socket)
        threading.Thread(target=server_socket.start, args=(global_config.listener_ip, listener_port)).start()
    sys.exit(app.exec_())