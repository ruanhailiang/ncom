import os.path
import struct
from osgeo import gdal
from osgeo import ogr
from osgeo import osr
from coordtransform import wgs84_to_gcj02, gcj02_to_wgs84

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


def export_shape_file(ncom_file, out_shape_file):
    """
    将ncom文件的gps弧度坐标转换为经纬度坐标，写入到shape文件中
    :param ncom_file:
    :param out_shape_file:
    :return: /
    """
    # 创建shape文件
    driver = ogr.GetDriverByName("ESRI Shapefile")
    if os.path.exists(out_shape_file):
        driver.DeleteDataSource(out_shape_file)
    ds = driver.CreateDataSource(out_shape_file)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    # 创建图层
    layer = ds.CreateLayer("Poi", geom_type=ogr.wkbPoint)
    layer.CreateField(ogr.FieldDefn("index", ogr.OFTInteger64))
    layer.CreateField(ogr.FieldDefn("rad_lat", ogr.OFTReal))
    layer.CreateField(ogr.FieldDefn("rad_lon", ogr.OFTReal))
    layer.CreateField(ogr.FieldDefn("deg_lat", ogr.OFTReal))
    layer.CreateField(ogr.FieldDefn("deg_lon", ogr.OFTReal))
    # 读取数据并写入shape文件
    ncom_fp = open(ncom_file, 'rb')
    print("开始将ncom转换为shape数据...")
    index = 0
    while True:
        info = ncom_fp.read(72)
        if not info:
            break
        rad_lat, rad_lon = struct.unpack('dd', info[23:39])
        deg_lat, deg_lon = rad_lat * RAD2DEG, rad_lon * RAD2DEG
        # 创建要素
        feature = ogr.Feature(layer.GetLayerDefn())
        feature.SetField("index", index)
        feature.SetField("rad_lat", rad_lat)
        feature.SetField("rad_lon", rad_lon)
        feature.SetField("deg_lat", deg_lat)
        feature.SetField("deg_lon", deg_lon)
        point = ogr.Geometry(ogr.wkbPoint)
        point.AddPoint(deg_lon, deg_lat)
        feature.SetGeometry(point)
        layer.CreateFeature(feature)
        index += 1

    ds.Destroy()
    ncom_fp.close()
    print("将数据ncom转换为shape完毕，共计%s条记录..." % (index, ))


def encoding_shape_file(in_shape_file, out_shape_file):
    """
    将输入shape文件的gps经纬度坐标加密后，写入到out shape file文件中
    :param in_shape_file:
    :param out_shape_file:
    :return:
    """
    print('坐标转换开始')
    in_ds = ogr.Open(in_shape_file)
    driver = ogr.GetDriverByName("ESRI Shapefile")
    if os.path.exists(out_shape_file):
        driver.DeleteDataSource(out_shape_file)
    driver.CopyDataSource(in_ds, out_shape_file)

    out_ds = ogr.Open(out_shape_file, update=1)
    out_layer = out_ds.GetLayer(0)
    for feature in out_layer:
        geometry = feature.GetGeometryRef()
        deg_lon = geometry.GetX()
        deg_lat = geometry.GetY()
        gcj_lng, gcj_lat = wgs84_to_gcj02(deg_lon, deg_lat)
        geometry.AddPoint(gcj_lng, gcj_lat)
        feature.SetGeometry(geometry)
        out_layer.SetFeature(feature)
    out_ds.Destroy()
    in_ds.Destroy()
    print("坐标转换完毕")


# 将shape文件几何坐标写入到ncom文件中
def write_ncom_file(shape_file, in_ncom_file, out_ncom_file):
    """
    将shape文件的经纬度坐标转换为弧度坐标后，写入到ncom文件中
    """
    print('开始将shape写入到ncom数据...')
    # 加载shape文件中几何数据
    ds = ogr.Open(shape_file)
    layer = ds.GetLayer(0)
    index_to_pack_data = {}
    for feature in layer:
        geometry = feature.GetGeometryRef()
        deg_lon = geometry.GetX()
        deg_lat = geometry.GetY()
        rad_lat, rad_lon = deg_lat * DEG2RAD, deg_lon * DEG2RAD
        pack_data = struct.pack('dd', rad_lat, rad_lon)
        feat_index = feature.GetField("index")
        if feat_index in index_to_pack_data:
            print("数据ID不正确")
        index_to_pack_data[feat_index] = pack_data
    ds.Destroy()
    # 根据ncom原文件及shape几何数据，写入转换后数据
    out_ncom_fp = open(out_ncom_file, 'wb')
    in_ncom_fp = open(in_ncom_file, 'rb')
    index = 0
    while True:
        info = in_ncom_fp.read(72)
        if not info:
            break
        if index not in index_to_pack_data:
            print("数据ID无法查询到")
        pack_data = index_to_pack_data[index]
        out_ncom_fp.write(info[:23])
        out_ncom_fp.write(pack_data)
        out_ncom_fp.write(info[39:])
        index += 1
    out_ncom_fp.close()
    in_ncom_fp.close()
    print("将数据shape转换为ncom数据完毕，共计%s条记录..." % (index,))


def test():
    ncom_file = r'D:\code\python\pycharm_code\FOXTROT_RFR944_20210312_135514.ncom'
    out_ncom_file = os.path.splitext(ncom_file)[0] + "_new.ncom"
    ncom_fp = open(ncom_file, 'rb')
    out_ncom_fp = open(out_ncom_file, 'wb')
    while True:
        info = ncom_fp.read(72)
        if not info:
            break
        rad_lat, rad_lon = struct.unpack('dd', info[23:39])
        pack_data = struct.pack('dd', rad_lat+1, rad_lon+1)
        out_ncom_fp.write(info[:23])
        out_ncom_fp.write(pack_data)
        out_ncom_fp.write(info[39:])
    out_ncom_fp.close()
    ncom_fp.close()


def test1():
    # ncom to shape
    ncom_file = r'D:\code\python\pycharm_code\FOXTROT_RFR944_20210312_135514.ncom'
    no_ext_ncom_file = os.path.splitext(ncom_file)[0]
    tmp_shape_file = r"D:\code\python\pycharm_code\poi.shp"

    export_shape_file(ncom_file, tmp_shape_file)
    # # shape to GCJ_02
    # out_shape_file = no_ext_ncom_file + ".shp"
    # encoding_shape_file(tmp_shape_file, out_shape_file)
    #
    # # shape to ncom
    # out_ncom_file = no_ext_ncom_file + '_out.ncom'
    # write_ncom_file(out_shape_file, ncom_file, out_ncom_file)


def main():
    # ncom to shape
    ncom_file = r'D:\code\python\pycharm_code\FOXTROT_RFR944_20210312_135514.ncom'
    no_ext_ncom_file = os.path.splitext(ncom_file)[0]
    tmp_shape_file = no_ext_ncom_file + "_tmp.shp"

    export_shape_file(ncom_file, tmp_shape_file)
    # shape to GCJ_02
    out_shape_file = no_ext_ncom_file + ".shp"
    encoding_shape_file(tmp_shape_file, out_shape_file)

    # shape to ncom
    out_ncom_file = no_ext_ncom_file + '_out.ncom'
    write_ncom_file(out_shape_file, ncom_file, out_ncom_file)


if __name__ == '__main__':
    main()
    #test1()
    # test()
