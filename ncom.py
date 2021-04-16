import os
import sys
import time
import struct
import argparse
import logging
from coordtransform import wgs84_to_gcj02
from ext_path.path import get_ext_files

"""
sync 1 B
time 2 H
acceleration_x 3 f
acceleration_y 3 f
acceleration_z 3 f
angular_rate_x 3 f
angular_rate_y 3 f
angular_rate_z 3 f
navigation_status 1 B
checksum_1 1 B
latitude 8 d
longitude 8 d
altitude 4 f
north_velocity 3 f
east_velocity 3 f
down_velocity 3 f
heading 3 f
pitch 3 f
roll 3 f
checksum_2 1 B
status_channel 1 B
"""

RAD2DEG = 180.0 / 3.1415926535897932384626433832795  # PI
DEG2RAD = 3.1415926535897932384626433832795 / 180.0  # PI
BLOCK_SIZE = 72


logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)
# 文件日志处理器
localtime = str(time.strftime("%Y-%m-%d_%H_%M_%S", time.localtime()))
log_path = os.path.join(os.getcwd(), 'logs')
if not os.path.exists(log_path):
    os.makedirs(log_path)
handler = logging.FileHandler(log_path + "\\log_%s.txt" % (localtime,))
formatter = logging.Formatter("%(asctime)s - %(levelname)s: %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
# 打印日志处理器
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logger.addHandler(console)


def is_valid_packet(packet_data):
    """
    验证数据校验和是否正确
    :param packet_data:
    :return:
    """
    checksum1 = uchar_checksum(packet_data[1:22])
    checksum2 = uchar_checksum(packet_data[1:61])
    checksum3 = uchar_checksum(packet_data[1:71])
    src_checksum1 = struct.unpack('B', packet_data[22:23])[0]
    src_checksum2 = struct.unpack('B', packet_data[61:62])[0]
    src_checksum3 = struct.unpack('B', packet_data[71:])[0]
    if checksum1 != src_checksum1 or checksum2 != src_checksum2 or checksum3 != src_checksum3:
        return False
    return True


def get_updated_checksum_data(packet_data):
    sync = packet_data[0:1]
    block1 = packet_data[1:22]
    block2 = packet_data[23:61]
    block3 = packet_data[62:71]

    checksum1 = uchar_checksum(block1)
    data = block1 + struct.pack('B', checksum1)

    checksum2 = uchar_checksum(data + block2)
    data += block2 + struct.pack('B', checksum2)

    checksum3 = uchar_checksum(data + block3)
    data += block3 + struct.pack('B', checksum3)

    return sync + data


def encoding_ncom_file(in_ncom_file, out_ncom_file):
    # 根据ncom原文件及shape几何数据，写入转换后数据
    out_ncom_dirname = os.path.dirname(out_ncom_file)
    if not os.path.exists(out_ncom_dirname):
        os.makedirs(out_ncom_dirname)
    out_ncom_fp = open(out_ncom_file, 'wb')
    in_ncom_fp = open(in_ncom_file, 'rb')
    index = 0
    error_num = 0
    while True:
        info = in_ncom_fp.read(BLOCK_SIZE)
        if not info:
            break
        index += 1
        if not is_valid_packet(info):
            error_num += 1
            out_ncom_fp.write(info)
            continue
        # 坐标转换
        rad_lat, rad_lon = struct.unpack('dd', info[23:39])
        deg_lat, deg_lon = rad_lat * RAD2DEG, rad_lon * RAD2DEG
        gcj_lng, gcj_lat = wgs84_to_gcj02(deg_lon, deg_lat)
        new_rad_lat, new_rad_lon = gcj_lat * DEG2RAD, gcj_lng * DEG2RAD
        # 重构数据
        pack_data = struct.pack('dd', new_rad_lat, new_rad_lon)
        new_info = info[:23] + pack_data + info[39:]
        new_info = get_updated_checksum_data(new_info)
        out_ncom_fp.write(new_info)

    out_ncom_fp.close()
    in_ncom_fp.close()
    msg = 'ncom共计: %s条记录,转换完毕:%s,未转换: %s...' % (index, index-error_num, error_num)
    if index <= 0 or error_num / index < 0.8:
        logger.error(msg)
    else:
        logger.info(msg)


def char_checksum(data, byteorder='little'):
    """
    char_checksum 按字节计算校验和。每个字节被翻译为带符号整数
    @param data: 字节串
    @param byteorder: 大/小端
    """
    length = len(data)
    checksum = 0
    for i in range(0, length):
        x = int.from_bytes(data[i:i + 1], byteorder, signed=True)
        if x > 0 and checksum > 0:
            checksum += x
            if checksum > 0x7F:  # 上溢出
                checksum = (checksum & 0x7F) - 0x80  # 取补码就是对应的负数值
        elif x < 0 and checksum < 0:
            checksum += x
            if checksum < -0x80:  # 下溢出
                checksum &= 0x7F
        else:
            checksum += x  # 正负相加，不会溢出

    return checksum


def uchar_checksum(data, byteorder='little'):
    """
    char_checksum 按字节计算校验和。每个字节被翻译为无符号整数
    @param data: 字节串
    @param byteorder: 大/小端
    """
    length = len(data)
    checksum = 0
    for i in range(0, length):
        checksum += int.from_bytes(data[i:i + 1], byteorder, signed=False)
        checksum &= 0xFF  # 强制截断

    return checksum


def main(args):
    ncom_files = get_ext_files(args.in_path, "NCOM")
    count = len(ncom_files)
    for index, ncom_file in enumerate(ncom_files):
        logger.info("转换文件开始 %s / %s [ %s ]" % (index, count, ncom_file))
        out_ncom_file = os.path.join(args.out_path, ncom_file[len(args.in_path)+1:])
        encoding_ncom_file(ncom_file, out_ncom_file)
        logger.info("转换文件完毕 %s / %s [ %s ]" % (index, count, ncom_file))
    input("程序运行完毕！请按回车键结束...")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='NCOM文件的WGS84坐标转换火星坐标工具')
    parser.add_argument('-i', '--input_file_path', help='转换前ncom文件目录', dest='in_path', type=str)
    parser.add_argument('-o', '--out_file_path', help='转换后ncom文件目录', dest='out_path', type=str)
    args = parser.parse_args()

    if not any(vars(args).values()):
        msg = "程序参数不正确，未运行"
        print("*" * 15 + "**" * len(msg) + "*" * 15)
        print("*" * 15 + msg + "*" * 15)
        print("*" * 15 + "**" * len(msg) + "*" * 15)
        parser.print_help()
        print("*" * 15 + "**" * len(msg) + "*" * 15)
        print("*" * 15 + "**" * len(msg) + "*" * 15)
        sys.exit(1)
    if not os.path.exists(args.in_path) or not os.path.exists(args.out_path):
        msg = "输入或输出路径不正确，未运行"
        print("*" * 15 + "**" * len(msg) + "*" * 15)
        print("*" * 15 + msg + "*" * 15)
        print("*" * 15 + "**" * len(msg) + "*" * 15)
        sys.exit(1)
    main(args)
