import os
import numpy as np  
import pandas as pd  
import time
import socket  
from scipy.interpolate import interp1d  
from scipy.optimize import curve_fit  
from scipy.signal import find_peaks 
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import Process, Queue, Value, Event
from queue import Empty  # 导入 queue.Empty

# cut the multiple peaks to single, then analysethem
def cut_the_peaks(data):
    try:
        sorted_data = data[np.argsort(data[:, 0])]
        # save_file = 'recv_sort.csv'
        # pd.DataFrame(sorted_data).to_csv(save_file, header=None, index=False)
        Intensity = sorted_data[:,1]
        Wavelength = sorted_data[:,0]
        # 分割
        peaks, _ = find_peaks(Intensity, height = np.max(Intensity)/3, distance = 50)
        cut_line_end = [0, len(Intensity) - 1]
        for index in range(len(peaks)- 1):
            cut_line_end = np.insert(cut_line_end, index + 1, (peaks[index] + peaks[index + 1])//2)
        # 传输片段数据
        find_fbgs_result = np.zeros(shape=(3, 1))
        for index in range(len(cut_line_end) - 1):
            peak_value, peak_coordinate = process_guass_fit(Wavelength[cut_line_end[index]: cut_line_end[index + 1]], Intensity[cut_line_end[index]: cut_line_end[index + 1]])
            find_fbgs_result[index] = peak_coordinate    
        # print(find_fbgs_result)
        return len(peaks), find_fbgs_result.flatten()

    except Exception as e:  
        print(f"Error cut the data: {e}")
        return None

# 找到峰值  
def find_peak(popt):  
    if popt is None:  
        return np.nan, np.nan  
    # 拟合得到的参数：幅度，中心  
    peak_value = popt[0]  # 幅度  
    peak_coordinate = popt[1]  # 中心  
    return peak_value, peak_coordinate  

# 定义高斯函数  
def gaussian(x, a, b, c):  
    return a * np.exp(-((x - b) / c) ** 2)  

# 使用高斯拟合并寻找峰值  
def fit_gaussian(x_data, y_data):  
    initial_guess = [max(y_data), np.mean(x_data), np.std(x_data)]  
    # 进行高斯拟合  
    try:  
        popt, _ = curve_fit(gaussian, x_data, y_data, p0=initial_guess)  
    except RuntimeError:  
        print("Could not fit Gaussian")  
        return None, None  
    return popt  # 返回拟合参数  

def process_guass_fit(x_data, y_data):
    
    ## 预处理
    # 查找数据高度的最大值和其半高宽  
    max_value = np.max(y_data)  
    half_max = max_value / 3  
    # 查找半高宽的两端坐标  
    left_index = np.where(y_data >= half_max)[0][0]  # 第一个大于等于半高宽的索引  
    right_index = np.where(y_data >= half_max)[0][-1]  # 最后一个大于等于半高宽的索引  
    # 输出半高宽的两端坐标  
    fwhm_coords = (left_index, right_index)
    # 裁剪数据  
    x_data = x_data[fwhm_coords[0]: fwhm_coords[1]]  
    y_data = y_data[fwhm_coords[0]: fwhm_coords[1]]  
    # 数据插值  
    # x_interpolated, data_interpolated = interpolate_data(data, x_data, factor=10) 
    
    # 进行高斯拟合  
    popt = fit_gaussian(x_data, y_data)  
    # 找到峰值  
    peak_value, peak_coordinate = find_peak(popt)  

    return peak_value, peak_coordinate  

# 建立UDP连接  
def Udp_open(queue, stop_event):
    try:  
        # 获取本地IP端口  
        local_ip = '192.168.0.4'  
        # local_ip = '180.209.3.214'
        local_port = 2599  

        # 输入有效性检查  
        # 检查IP地址格式  
        socket.inet_aton(local_ip)  # 对于IPv4地址  
        # 检查端口号  
        if local_port < 1 or local_port > 65535:  
            raise ValueError("Port number must be between 1 and 65535.")  

        # 实例化UDP套接字  
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  

        # 绑定UDP套接字  
        sock.bind((local_ip, local_port))  
        print(f"UDP socket bound to {local_ip}:{local_port}")  
        
        # 清空缓冲区  
        clear_udp_buffer(sock)  
        
        # 持续读取数据  
        while not stop_event.is_set():  # 检查停止事件:  
            Udp_read_period(sock, queue, stop_event)  

    except socket.error as e:  
        print(f"Invalid address: {e}")  
    except ValueError as e:  
        print(f"Invalid input: {e}")  
    except Exception as e:  
        print(f"Unexpected error: {e}")  
    finally:  
        sock.close()  # 确保关闭套接字  

def clear_udp_buffer(sock):  
    try:  
        # 循环读取，直到没有更多的待处理数据  
        while True:  
            # 设置时间限制，避免无限循环  
            sock.settimeout(1)  # 设置超时为1000毫秒  
            try:  
                data, addr = sock.recvfrom(2048)  # 尝试接收数据  
                print(f"Clearing buffer: Received data from {addr}")  
            except socket.timeout:  
                break  # 超时后退出循环  
    except Exception as e:  
        print(f"Error clearing buffer: {e}")  

def recv_checked_data(sock, check_header, static_len, stop_event):
    data = []
    while(not stop_event.is_set() and (len(data) == 0 or data[0:4] != bytes.fromhex(check_header))):
        data, addr = sock.recvfrom(static_len)  # 设置接收的最大字节数
        while (not stop_event.is_set() and len(data) < static_len):
            part, addr = sock.recvfrom(static_len - len(data))  # 接收剩余的数据
            data += part  # 拼接数据
    if stop_event.is_set():
        return None
    return data[4:]

def Udp_read_period(sock, queue, stop_event):  
    # storage_array = []  # 将数组初始化在函数内，避免多次调用时出现问题  
    try:  
        static_len = 1204
        start_time = time.time()
        points = np.zeros(shape=(1800, 2))
        # 设置接收数据缓冲区大小  
        data = recv_checked_data(sock, "01010101", static_len, stop_event)
        if stop_event.is_set():
            return None
        points[0:300, :] = process_udp_data(data)  # 调用数据处理函数 

        data = recv_checked_data(sock, "02020202", static_len, stop_event)
        if stop_event.is_set():
            return None
        points[300:600, :] = process_udp_data(data)  # 调用数据处理函数  

        data = recv_checked_data(sock, "03030303", static_len, stop_event)
        if stop_event.is_set():
            return None
        points[600:900, :] = process_udp_data(data)  # 调用数据处理函数  
        
        data = recv_checked_data(sock, "04040404", static_len, stop_event)
        if stop_event.is_set():
            return None
        points[900:1200, :] = process_udp_data(data)  # 调用数据处理函数  
        
        data = recv_checked_data(sock, "05050505", static_len, stop_event)
        if stop_event.is_set():
            return None
        points[1200:1500, :] = process_udp_data(data)  # 调用数据处理函数 
        
        data = recv_checked_data(sock, "06060606", static_len, stop_event)
        if stop_event.is_set():
            return None
        points[1500:1800, :] = process_udp_data(data)  # 调用数据处理函数 
        
        queue.put(points)  # 将完整数据放入队列

        return None  

    except Exception as e:  
        print(f"Error reading datagram: {e}")  
        return None  


def process_udp_data(data):  
    # 确保数据长度是4的倍数  
    if len(data) % 4 != 0:  
        print(len(data))
        raise ValueError("Data length must be a multiple of 4")  

    if len(data) !=  1200:
        print(len(data))
        raise ValueError("Data length must be 1200")

    points = []  
    # 每4个字节提取一次  
    for i in range(0, len(data), 4):  
        # 提取4个字节  
        group = data[i:i + 4]  
        # 拼接x和y坐标  
        x = (group[1] << 8) + group[0]  # 前两个字节作为x坐标  
        y = (group[3] << 8) + group[2]  # 后两个字节作为y坐标  
        points.append((x, y))  

    return np.array(points)  

def Udp_data_pro(queue, counter, stop_event, Threshold_num):
    print(f"processer stated!:{os.getpid()}")
    while not stop_event.is_set():
        process_recv_data(queue, counter, stop_event, Threshold_num)
    print(f"processer ended!:{os.getpid()}")

def process_recv_data(queue, counter, stop_event, Threshold_num):
    while queue.empty():
        if counter.value >= Threshold_num:
            stop_event.set()  # 设置停止事件
            print(counter.value)
            return None
        time.sleep(0.01)

    try:  
        data = queue.get(timeout=0.01)  # 从队列中获取数据  # 0.01秒超时  
    except Empty:
        return None
    # print(counter.value)
    # fbgs_results = np.zeros(shape=(3, 10))
    result = cut_the_peaks(np.array(data))
    if result is not None:  
        # peaks_nums, fbgs_results[:, 0] = result
        peaks_nums, _ = result
        # print(result)
        # print(fbgs_results[:, 0]) #########################################################################
    else:  
        print("Error occurred while cutting peaks.")  
        return None  # 或者处理错误的逻辑
    if (peaks_nums < 3):
        print(f"\n peaks_nums = {peaks_nums}")
    with counter.get_lock():  # 确保对值的原子更新  
        counter.value += 1  # 自增计数器
    if counter.value >= Threshold_num:
        stop_event.set()  # 设置停止事件
    
    # save_file = 'res_test_tran.csv'
    # pd.DataFrame(fbgs_results).to_csv(save_file, header=None, index=False)

    return None

def main():
    
    Threshold_num = 100000

    queue = Queue()  # 创建共享队列  
    counter = Value('i', 0)  # 创建共享整数（初始值为0）  
    stop_event = Event()  # 创建停止事件
 
    # 启动接收进程  
    receiver_process = Process(target=Udp_open, args=(queue, stop_event))  
    receiver_process.start()  

    # 启动多个处理进程  
    num_processors = 3  # 根据需要调整处理进程数量  
    processor_processes = []  
    for _ in range(num_processors):  
        processor = Process(target=Udp_data_pro, args=(queue, counter, stop_event, Threshold_num))  
        processor.start()  
        processor_processes.append(processor)  
    
    start_time = time.time()  

    # 等待进程结束  
    receiver_process.join()  
    print("receiver_process joined!")
     # 设置停止事件，等待处理进程结束  
    # stop_event.set()  # 发送停止信号给处理进程
    for processor in processor_processes: 
        processor.join()
    print("processor_process joined!")
    end_time = time.time() 

    print(f"Total time for {Threshold_num} fittings: {end_time - start_time:.4f} seconds")


if __name__ == "__main__":  
    main()