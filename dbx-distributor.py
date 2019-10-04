"""Download all files from an appfolder or upload specific files an appfolder.

This app uses Dropbox API v2.
"""

import datetime
import os
# import six
import sys
import time
import unicodedata
import dotenv
from dropbox_content_hasher import DropboxContentHasher

if sys.version.startswith('2'):
    sys.exit("ERROR: Python2 detected. Please use with Python3")

import dropbox
from dotenv import load_dotenv
load_dotenv()


def main():
    """Main program.
    """
    TOKEN = os.getenv("TOKEN")
    folder = os.getenv("folder")
    rootdir = os.getenv("rootdir")
    # rootdir = os.path.expanduser(os.getenv("rootdir"))
    # for root, dirs, files in os.walk(rootdir):
    #     for name in files: 
    #         fullname = os.path.join(root, name)
    #         print(fullname)

    print('Dropbox folder name:', folder)
    print('Local directory:', rootdir)
    if not os.path.exists(rootdir):
        print(rootdir, 'does not exist on your filesystem')
        sys.exit(1)
    elif not os.path.isdir(rootdir):
        print(rootdir, 'is not a folder on your filesystem')
        sys.exit(1)

    dbx = dropbox.Dropbox(TOKEN)
    listing = list_folder(dbx, folder, "")
    video_files = os.listdir(rootdir)

    for dbx_file in listing:
        found = False
        print('hunting for ', dbx_file)
        if dbx_file in video_files:
            # print('Found file and need to test if it needs updating')
            fullname = os.path.join(rootdir, dbx_file)
            md = listing[dbx_file]
            mtime = os.path.getmtime(fullname)
            mtime_dt = datetime.datetime(*time.gmtime(mtime)[:6])
            size = os.path.getsize(fullname)
            if check_hash(fullname) == md.content_hash:
                print(dbx_file, 'is already synced [stats match]')
            else:
                print(dbx_file, 'exists with different stats, downloading')
                res = download(dbx, folder, "", dbx_file)
                with open(fullname) as f:
                    data = f.read()
                    if res == data:
                        print(dbx_file, 'is already synced [content match]')
                        f.close()
                    else:
                        with open(fullname, 'wb') as f:
                            data = f.write(res)
                            f.close()

        if dbx_file not in video_files:
            fullname = os.path.join(rootdir, dbx_file)
            print(fullname)
            print(dbx_file, 'does not exist, downloading')
            # open(fullname, 'a').close()
            res = download(dbx, folder, "", dbx_file)
            with open(fullname, 'wb') as f:
                data = f.write(res)
                f.close()
            # os.utime(fullname, (int(md.client_modified.strftime('%Y%m%d')), int(md.client_modified.strftime('%Y%m%d'))))
            
    sys.exit()
    

    if args.mode == "up":
        for root, dirs, files in os.walk(rootdir):
            subfolder = ""
            # subfolder = root[len(rootdir):].strip(os.path.sep)
            listing = list_folder(dbx, folder, subfolder)
            print('Descending into', subfolder, '...')

            for name in files: 
                fullname = os.path.join(root, name)

            continue

            # First do all the files.
            for name in files:
                fullname = os.path.join(root, name)
                # if not isinstance(name, six.text_type):
                #     name = name.decode('utf-8')
                nname = unicodedata.normalize('NFC', name)
                if name.startswith('.'):
                    print('Skipping dot file:', name)
                elif name.startswith('@') or name.endswith('~'):
                    print('Skipping temporary file:', name)
                elif name.endswith('.pyc') or name.endswith('.pyo'):
                    print('Skipping generated file:', name)
                elif nname in listing:
                    md = listing[nname]
                    mtime = os.path.getmtime(fullname)
                    mtime_dt = datetime.datetime(*time.gmtime(mtime)[:6])
                    size = os.path.getsize(fullname)
                    if (isinstance(md, dropbox.files.FileMetadata) and
                            mtime_dt == md.client_modified and size == md.size):
                        print(name, 'is already synced [stats match]')
                    else:
                        print(name, 'exists with different stats, downloading')
                        res = download(dbx, folder, subfolder, name)
                        with open(fullname) as f:
                            data = f.read()
                        if res == data:
                            print(name, 'is already synced [content match]')
                        else:
                            print(name, 'has changed since last sync')
                            upload(dbx, fullname, folder, subfolder, name, overwrite=True)
                else:
                    upload(dbx, fullname, folder, subfolder, name)

            # Then choose which subdirectories to traverse.
            keep = []
            for name in dirs:
                if name.startswith('.'):
                    print('Skipping dot directory:', name)
                elif name.startswith('@') or name.endswith('~'):
                    print('Skipping temporary directory:', name)
                elif name == '__pycache__':
                    print('Skipping generated directory:', name)
                elif yesno('Descend into %s' % name, True, args):
                    print('Keeping directory:', name)
                    keep.append(name)
                else:
                    print('OK, skipping directory:', name)
            dirs[:] = keep
    else:
        listing = list_folder(dbx, folder, "")

def list_folder(dbx, folder, subfolder):
    """List a folder.

    Return a dict mapping unicode filenames to
    FileMetadata|FolderMetadata entries.
    """
    path = '/%s/%s' % (folder, subfolder.replace(os.path.sep, '/'))
    while '//' in path:
        path = path.replace('//', '/')
    path = path.rstrip('/')
    try:
        res = dbx.files_list_folder(path)
    except dropbox.exceptions.ApiError as err:
        print('Folder listing failed for', path, '-- assumed empty:', err)
        return {}
    else:
        rv = {}
        for entry in res.entries:
            rv[entry.name] = entry
        return rv

def check_hash(fullname):
    hasher = DropboxContentHasher()
    with open(fullname, 'rb') as f:
        while True:
            chunk = f.read(1024)
            if len(chunk) == 0:
                break
            hasher.update(chunk);
    digest = hasher.hexdigest()
    return digest

def download(dbx, folder, subfolder, name):
    """Download a file.

    Return the bytes of the file, or None if it doesn't exist.
    """
    path = '/%s/%s/%s' % (folder, subfolder.replace(os.path.sep, '/'), name)
    while '//' in path:
        path = path.replace('//', '/')
    # with stopwatch('download'):
    try:
        md, res = dbx.files_download(path)
    except dropbox.exceptions.HttpError as err:
        print('*** HTTP error', err)
        return None
    data = res.content
    print(len(data), 'bytes; md:', md)
    return data

def upload(dbx, fullname, folder, subfolder, name, overwrite=False):
    """Upload a file.

    Return the request response, or None in case of error.
    """
    path = '/%s/%s/%s' % (folder, subfolder.replace(os.path.sep, '/'), name)
    while '//' in path:
        path = path.replace('//', '/')
    mode = (dropbox.files.WriteMode.overwrite
            if overwrite
            else dropbox.files.WriteMode.add)
    mtime = os.path.getmtime(fullname)
    with open(fullname, 'rb') as f:
        data = f.read()
    with stopwatch('upload %d bytes' % len(data)):
        try:
            res = dbx.files_upload(
                data, path, mode,
                client_modified=datetime.datetime(*time.gmtime(mtime)[:6]),
                mute=True)
        except dropbox.exceptions.ApiError as err:
            print('*** API error', err)
            return None
    print('uploaded as', res.name.encode('utf8'))
    return res

if __name__ == '__main__':
    main()
