# fbg demodulatec cal
### 文件说明

#### real_data_guass.py

接收来自FPGA的UDP数据报，把切片后的数据重新组合并进行高斯曲线拟合，寻找峰值解调信息

output sample:

(guassvenv) oranbot@oranbot:~/DataLab$ python real_data_guass_0114.py 
UDP socket bound to 192.168.0.4:2599
processer stated!:16795
processer stated!:16796
processer stated!:16797
Error reading datagram: timed out
Error reading datagram: timed out
processer ended!:16795
100000
processer ended!:16797
receiver_process joined!
processer ended!:16796
processor_process joined!
Total time for 100000 fittings: 513.9177 seconds

#### FPGA-codes

包含fpga源文件的文件夹，主要实现ADC数据采集、存储与切片分段UDP发送，使用帧头标志位来确保切片片段的数据顺序。（以太网发送功能参考小梅哥FPGA源代码，修改后使用）

### 开发平台

解调上位机：树莓派4B

硬件采集+发送：ACX720开发板 + AD9226

### 开发中

ADC数据采集...

解调速度优化（>200Hz）