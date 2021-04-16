import os
import shutil


def copy_file_path(source_path, target_path):
    """复制源文件目录下的所有目录到另一个文件目录下"""
    for e, _, _ in os.walk(source_path):
        path_name = os.path.splitdrive(e)[1]
        file_path = os.path.join(target_path, path_name[len(source_path)-1:])
        if not os.path.exists(file_path):
            os.makedirs(file_path)


def copy_files(source_path, target_path):
    """复制一个文件夹所有文件到另一个文件夹"""
    for source_file_Path, d, filelist in os.walk(source_path):
        drivename, pathname = os.path.splitdrive(source_file_Path)
        file_path = os.path.join(target_path, pathname)
        if not os.path.exists(file_path):
            os.makedirs(file_path)
        for filename in filelist:
            file = os.path.join(source_file_Path, filename)
            shutil.copy(file, file_path)


def get_files(path, file_name, is_lower=False):
    """根据文件名与文件目录，获取目录下所有文件列表"""
    files = []
    for eachfilePath, d, file_names in os.walk(path):
        for name in file_names:
            if is_lower:
                if name == file_name:
                    tempfile = os.path.join(eachfilePath, name)
                    files.append(tempfile)
            else:
                if name.lower() == file_name.lower():
                    tempfile = os.path.join(eachfilePath, name)
                    files.append(tempfile)

    return files


def get_ext_files(path, ext_name):
    # .exe的后缀为extension_name,后缀名中不允许有"."
    filelists = []
    for eachfilePath, d, file_names in os.walk(path):
        for name in file_names:
            if name.split(".")[-1].lower() == ext_name.lower():
                tempfile = os.path.join(eachfilePath, name)
                filelists.append(tempfile)
    return filelists


if __name__ == '__main__':
    pass
