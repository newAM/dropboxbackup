# Dropbox Backup Script

Quick and dirty backup script that uploads to Dropbox.

Uses the [Dropbox Python SDK](https://github.com/dropbox/dropbox-sdk-python).

## Setup
1. Install python 3.8 `apt install python3.8`
2. (Optional) setup a python venv
3. Install requirements `python3.8 -m pip install -r requirements.txt`
4. Create a dropbox app at https://www.dropbox.com/developers/apps
5. Generate a token for the app
6. Put the token in your keyring `keyring set dropbox token`

## Usage
Create a JSON file with a list of dictionaries.

Each dictionary has two keys, "path", and "name".

See included JSON files for an example.

```bash
python3.8 backup.py my_config.json
```
