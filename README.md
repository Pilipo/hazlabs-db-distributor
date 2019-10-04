# hazlabs-db-distributor
A Python-based Dropbox app that synchronizes media for onsite installations to automatically refresh content.

## Prerequisites
* Python 3
* modules
	* dotenv (`pip install python-dotenv`)
	* dropbox SDK (`pip install dropbox`)
	* six (`pip install six`)

## Setup Steps
1. Install the Dropbox Python SDK
2. Copy `sample.env` to `.env` and update the relevant variables
   * `TOKEN` must be the OAuth token generated at https://www.dropbox.com/developers/apps. It is strongly recommended that you use an appfolder, not full Dropbox access.
   * `rootdir` can be changed for synchronizing to a custom folder
3. Test success with `python ./dbx-distributor.py`
