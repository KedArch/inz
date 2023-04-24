#!/usr/bin/env python3
import sys
import json
import pathlib
import argparse
import requests

if sys.version_info < (3, 8):
  print("Minimal Python interpreter version required is 3.8")
  sys.exit(65)

parser = argparse.ArgumentParser(
  formatter_class=argparse.RawDescriptionHelpFormatter,
  description="Graylog setup script via REST API.\n"
  "Elements are directories in json directory representing sets of API endpoints."
  "\nParts are data sent to those API endpoints.",
  epilog="Error codes: "
       "\n65 - unsupported interpreter version\n66 - invalid argumets"
       "\n67 - Graylog setup error")
parser.add_argument(
  "-e", "--elements", dest="elements", nargs="*",
  required=not {"-l", "--list"} &
  set(sys.argv),
  help="element names")
parser.add_argument(
  "-i", "--skip-id", dest="skip_id", action="store_true",
  help="skip id in parts")
parser.add_argument(
  "-l", "--list", dest="list", action="store_true",
  help="list detected elements")
parser.add_argument(
  "-f", "--no-fail", dest="fail", action="store_true",
  help="do not fail on setup errors")
parser.add_argument(
  "-u", "--user", dest="user", default="admin",
  help="username to auth (default 'admin')")
parser.add_argument(
  "-p", "--pass", dest="passwd", default="admin",
  help="password to auth (default 'admin')")
parser.add_argument(
  "-d", "--url", dest="url", default="http://127.0.0.1:9000",
  help="graylog URL (default 'http://127.0.0.1:9000')")
parser.add_argument(
  "-v", "--verbose", dest="verbose", action="store_true",
  help="show more info")
args = parser.parse_args()

detected_elements = [i.name for i in pathlib.Path("json").iterdir() if i.is_dir()]
sorted(detected_elements)
if args.list:
  print("Detected elements:\n"+"\n".join(detected_elements))
  sys.exit(0)

elements = args.elements
skip_ids = args.skip_id
user = args.user
fail = args.fail
passwd = args.passwd
url = args.url
verbose = args.verbose
basepath = pathlib.Path(__file__).parent

API_ENDPOINT = f"{url}/api/"
AUTH = (user, passwd)
HEADERS = {
  'Accept': 'application/json',
  'Content-Type': 'application/json',
  'Accept-Encoding': 'gzip, deflate',
  'X-Requested-By': 'cli',
}

def delete_ids(obj):
  if isinstance(obj, dict):
    for key in list(obj.keys()):
      if key == 'id':
        del obj[key]
      else:
        delete_ids(obj[key])
  elif isinstance(obj, list):
    for item in obj:
      delete_ids(item)

def setup(what):
  for what_one in what:
    path = pathlib.Path(__file__).parent.resolve().joinpath("json/"+what_one)
    files = list(path.glob('**/*.json'))
    for file in files:
      with file.open(mode="r") as f:
        data = f.read()
      data = json.loads(data)
      if skip_ids:
        data = delete_ids(data)
      file_api_endpoint = API_ENDPOINT\
        +str(file.parent.relative_to(basepath/"json"/what_one))
      response = requests.post(
        file_api_endpoint,
        headers=HEADERS,
        json=data,
        auth=AUTH,
      )
      if response.status_code != 201:
        print(f"Error occured when sending data of {file.stem}")
        print(response.status_code, response.reason)
        if verbose:
            print(f"API endpoint: {file_api_endpoint}")
            print(f"JSON: \n{data}")
        if not fail:
            print("Stopping because of setup error")
            sys.exit(67)
      else:
        print(f'Successfully set {file.stem}')
    print(f"Went through all parts of element {what_one}")

if elements:
  decheck = set(detected_elements)
  echeck = set(elements)
  diff = echeck.difference(decheck)
  if len(diff) != 0:
    print("Couldn't find provided elements:\n"+"\n".join(diff))
    sys.exit(66)
  setup(elements)
