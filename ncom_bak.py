import os.path
import struct
from osgeo import gdal
from osgeo import ogr
from osgeo import osr
from coordtransform import wgs84_to_gcj02, gcj02_to_wgs84
import binascii

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
    print("将数据shape转换为ncom数据完毕，共计%s条记录..." % (index,))


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


def main():
    ncom_file = r'D:\data\ncom\GE20_DC1E0031_1_RTBGPS_IN_20200830T073047_20200830T082112.ncom'
    no_ext_ncom_file = os.path.splitext(ncom_file)[0]
    out_ncom_file = no_ext_ncom_file + '_out.ncom'
    encoding_ncom_file(ncom_file, out_ncom_file)


if __name__ == '__main__':
    main()
    # test1()
