"""Download all files from an appfolder or upload specific files an appfolder.

This app uses Dropbox API v2.
"""

import datetime
import os
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

    print('Dropbox subfolder name:', folder)
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

    for name in video_files: # Check for files that have been removed from DB
        if name not in listing:
            fullname = os.path.join(rootdir, name)
            print("Whomp whomp! {0} does not exist in cloud".format(name))
            print("Deleting file now")
            os.remove(fullname)

    for dbx_file in listing: # Download new and updated files from DB
        found = False
        if dbx_file in video_files:
            fullname = os.path.join(rootdir, dbx_file)
            md = listing[dbx_file]
            mtime = os.path.getmtime(fullname)
            mtime_dt = datetime.datetime(*time.gmtime(mtime)[:6])
            size = os.path.getsize(fullname)
            if check_hash(fullname) == md.content_hash:
                print('Sync Status: {1:<20} Already Synced: {0}'.format(dbx_file, "[stats matched]"))
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
            res = download(dbx, folder, "", dbx_file)
            with open(fullname, 'wb') as f:
                data = f.write(res)
                f.close()            

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
