import numpy as np  
import pandas as pd  
import time
import socket  
from scipy.interpolate import interp1d  
from scipy.optimize import curve_fit  
from scipy.signal import find_peaks 
from concurrent.futures import ProcessPoolExecutor


# read data from csv file
def read_data_from_csv(file_path):
    try:
        df = pd.read_csv(file_path, header=None)  
        data = df.values  # 或者使用 df.to_numpy() 
        if(len(data) < 200):
            print("Warning: data length less 200. please check the data.")
    
        return data

    except Exception as e:  
        print(f"Error reading the CSV file: {e}")  
        return None
# cut the multiple peaks to single, then analysethem
def cut_the_peaks(data):
    try:
        Intensity = data[:,1]
        Wavelength = data[:,0]
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
def Udp_open():  
    try:  
        # 获取本地IP端口  
        local_ip = '192.168.0.4'  
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
        while True:  
            Udp_read_period(sock)  

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
            sock.settimeout(0.1)  # 设置超时为100毫秒  
            try:  
                data, addr = sock.recvfrom(2048)  # 尝试接收数据  
                print(f"Clearing buffer: Received data from {addr}")  
            except socket.timeout:  
                break  # 超时后退出循环  
    except Exception as e:  
        print(f"Error clearing buffer: {e}")  

def Udp_read_period(sock):  
    storage_array = []  # 将数组初始化在函数内，避免多次调用时出现问题  

    try:  
        internal_data = []
        # 设置接收数据缓冲区大小  
        data, addr = sock.recvfrom(1208)  # 设置接收的最大字节数
        internal_data[0:1200] = data[8:]  # 提取UDP负载
        data, addr = sock.recvfrom(1208)  # 设置接收的最大字节数
        internal_data[1200:2400] = data[8:]
        data, addr = sock.recvfrom(1208)  # 设置接收的最大字节数
        internal_data[240:3600] = data[8:]
        data, addr = sock.recvfrom(1208)  # 设置接收的最大字节数
        internal_data[3600:4800] = data[8:]
        data, addr = sock.recvfrom(1208)  # 设置接收的最大字节数
        internal_data[4800:6000] = data[8:]
        data, addr = sock.recvfrom(1060)  # 设置接收的最大字节数
        internal_data[6000:7060] = data[8:]
        # print(f"Received {len(data)} bytes of data from {addr}: {data}")  

        # 检查接收到的数据长度 
        if len(data) >= 8:  
            # 处理接收到的数据
            points = process_udp_data(internal_data)  # 调用数据处理函数  
            storage_array.append(points)  # 存储处理结果  

            # 打印处理结果  
            print(f"Processed points: {points}")  
            return points  
        else:  
            print("Received data is smaller than 8 bytes, unable to extract internal data.")  
            return None  

    except Exception as e:  
        print(f"Error reading datagram: {e}")  
        return None  


def process_udp_data(data):  
    # 确保数据长度是4的倍数  
    if len(data) % 4 != 0:  
        print(len(data))
        raise ValueError("Data length must be a multiple of 4")  

    points = []  
    # 每4个字节提取一次  
    for i in range(0, len(data), 4):  
        # 提取4个字节  
        group = data[i:i + 4]  
        # 拼接x和y坐标  
        x = (group[1] << 8) + group[0]  # 前两个字节作为x坐标  
        y = (group[3] << 8) + group[2]  # 后两个字节作为y坐标  
        points.append((x, y))  

    return points  

def main():
    
    Udp_open()
    
    # 记录开始时间  
    start_time = time.time()  

    fbgs_results = np.zeros(shape=(3, 10))
    heltz = 40

    for index in range(10):
        file_name = str(heltz) + 'HZ_' + str(index+1) + '_raw.csv'
        peaks_nums,fbgs_results[:, index]  = cut_the_peaks(read_data_from_csv('fbg_data.csv')) 
        if (peaks_nums < 3):
            print(f"\n peaks_nums = {peaks_nums}")

    # print(fbgs_results)
    save_file = str(heltz) + 'HZ_' + 'fbgs_results.csv'
    pd.DataFrame(fbgs_results).to_csv(save_file, header=None, index=False)

    # 记录结束时间  
    end_time = time.time()  
    total_time = end_time - start_time  # 计算总耗时   
    # 打印总耗时  
    print(f"Total time for {10} fittings: {total_time:.4f} seconds")

if __name__ == "__main__":  
    main()