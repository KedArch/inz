#!/usr/bin/env python3
import sys
import json
import pathlib
import argparse
import datetime
import requests

if sys.version_info < (3, 8):
  print("Minimal Python interpreter version required is 3.8")
  sys.exit(65)

parser = argparse.ArgumentParser(
  formatter_class=argparse.RawDescriptionHelpFormatter,
  description="Graylog setup script via REST API.\n"
  "Elements are directories in json directory representing sets of API endpoints."
  "\nJSONs are data sent to those API endpoints.",
  epilog="Error codes: "
       "\n65 - unsupported interpreter version\n66 - invalid argumets"
       "\n67 - Graylog setup error")
parser.add_argument(
  "elements", nargs="*",
  help="element names")
parser.add_argument(
  "-l", "--list", dest="list", action="store_true",
  help="list detected elements")
parser.add_argument(
  "-f", "--no-fail", dest="fail", action="store_true",
  help="do not fail on setup errors")
parser.add_argument(
  "-r", "--remove", dest="remove", action="store_true",
  help="remove resource if exists on remote (also dependants)")
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

detected_elements = [i.name for i in pathlib.Path("json").iterdir() if\
                      i.is_dir()]
sorted(detected_elements)
if args.list:
  print("Detected elements:\n"+"\n".join(detected_elements))
  sys.exit(0)

elements = args.elements
user = args.user
fail = args.fail
passwd = args.passwd
url = args.url
verbose = args.verbose
remove = args.remove
basepath = pathlib.Path(__file__).parent

API_ENDPOINT = f"{url}/api/"
AUTH = (user, passwd)
HEADERS = {
  'Accept': 'application/json',
  'Content-Type': 'application/json',
  'Accept-Encoding': 'gzip, deflate',
  'X-Requested-By': 'cli',
}

def search_nested_dict(dictionary, search_value):
  for key, value in dictionary.items():
    if str(key) == search_value:
      return True
    if isinstance(value, dict):
      if search_nested_dict(value, search_value):
        return True
  return False

def replace_nested_dict(dictionary, key_list, replace,
                        last_list=False, make_list=False, ind=0):
  if not key_list[ind] in dictionary.keys():
    return
  if len(key_list)-1 == ind:
    if last_list:
      if make_list:
        make_list = False
        dictionary[key_list[ind]] = []
      dictionary[key_list[ind]].append(replace)
    else:
      dictionary[key_list[ind]] = replace
    return dictionary
  dictionary[key_list[ind]] = replace_nested_dict(
      dictionary[key_list[ind]], key_list, replace, last_list, ind=ind+1)
  return dictionary

def get_file_dependants(root_dir, check_dict={}):
  file_deps = {}
  for file in pathlib.Path(root_dir).rglob("*.json"):
    if search_nested_dict(check_dict, str(file)):
      continue
    dep_dir_name = file.stem
    dep_dir = file.parent / dep_dir_name
    if dep_dir.is_dir():
      file_deps[file] = get_file_dependants(dep_dir, check_dict)
    else:
      file_deps[file] = None
    check_dict = file_deps.copy()
  return file_deps

def check_one(data, filedata):
  if data.get("title", "0") == filedata.get("title", "1"):
    if data.get("id", ""):
      return True, data["id"]
    else:
      return None, ""
  if data.get("username", "0") == filedata.get("username", "1"):
    return True, data["username"]
  return False, ""

def check_title(data, file, key):
  if isinstance(file, type(pathlib.Path())):
    with file.open() as f:
      filedata = json.loads(f.read())
  else:
    filedata = file
  if isinstance(data, type({})):
    if key in data.keys():
      for i in data[key]:
        err, idt = check_one(i, filedata)
        if err is not False:
          return err, idt
      else:
        return False, ""
  elif isinstance(data, type([])):
    for i in data:
      err, idt = check_one(i, filedata)
      if err is not False:
        return err, idt
    else:
      return False, ""
  return None, ""

def date_setup(data):
  setup = data["date_setup"]
  del data["date_setup"]
  if verbose:
    print(f"data:\n{data}")
    print(f"setup:\n{setup}")
  if not isinstance(setup, type([])):
    return
  for i in setup:
    now = datetime.datetime.utcnow()
    now = now.strftime('%Y-%m-%dT%H:%M:%S.%f+00:00')
    data = replace_nested_dict(data, (i,), now, False)
    if data is None:
      return
  return data

def id_setup_body(field, endpoint, title, data, file, level, last_list=False):
  err, get_data = get(API_ENDPOINT+endpoint, file, level)
  if err is not False:
    return
  err, idt = check_title(get_data, {"title": title},
                         endpoint.split("/")[-1])
  if not err:
    return
  data = replace_nested_dict(data, field, idt, last_list)
  return data

def id_setup(data, file, level):
  setup = data["id_setup"]
  del data["id_setup"]
  if verbose:
    print(f"data:\n{data}")
    print(f"setup:\n{setup}")
  for field, to_find in setup.items():
    field = field.split("/")
    if isinstance(to_find, type([])):
      for i in to_find:
        endpoint = list(i.keys())[0]
        title = list(i.values())[0]
        data = id_setup_body(field, endpoint, title, data, file, level, True)
        if data is None:
          return None
    else:
      endpoint = list(to_find.keys())[0]
      title = list(to_find.values())[0]
      data = id_setup_body(field, endpoint, title, data, file, level)
  return data

def get(endpoint, file, level):
  response = requests.get(
    endpoint,
    headers=HEADERS,
    auth=AUTH,
  )
  if verbose:
    print(f"GET API endpoint: {endpoint}")
    print("Response code:", response.status_code, response.reason)
    print(f"JSON received: \n{response.json() if response.text else None}")
  err = False
  if response.status_code == 404:
    err = None
  elif response.status_code != 200:
    err = True
    print(f"{'-'*level}GET of {file.relative_to(basepath/'json')} failed",
          end="")
    if not fail:
      print("\nStopping because of setup error")
      sys.exit(67)
  return err, response.json() if response.text else {}

def post(endpoint, file, data, level):
  response = requests.post(
    endpoint,
    headers=HEADERS,
    json=data,
    auth=AUTH,
  )
  if verbose:
    print(f"POST API endpoint: {endpoint}")
    print("Response code:", response.status_code, response.reason)
    print(f"JSON sent: \n{data}")
    print(f"JSON received: \n{response.json() if response.text else None}")
  if response.status_code > 299 or response.status_code < 200:
    print(f"{'-'*level}POST of {file.relative_to(basepath/'json')} failed",
          end="")
    if not fail:
      print("\nStopping because of setup error")
      sys.exit(67)
  rjson = response.json() if response.text else {}
  id = rjson.get("id", False)
  if id:
    return id
  for key, value in rjson.items():
    if key.endswith("id"):
      return value

def delete(endpoint, file, idt, level):
  if idt:
    response = requests.delete(
      endpoint+f"/{idt}",
      headers=HEADERS,
      auth=AUTH,
    )
    if verbose:
      print(f"DELETE API endpoint: {endpoint}")
      print("Response code:", response.status_code, response.reason)
      print(f"JSON received: \n{response.json() if response.text else None}")
    if response.status_code != 204:
      print(f"{'-'*level}couldn't remove {file.relative_to(basepath/'json')}")
    else:
      print(f"{'-'*level}Removed {file.relative_to(basepath/'json')}")
  else:
    print(f"{'-'*level}couldn't remove {file.relative_to(basepath/'json')}, "
          "it does not exist ")

def do_what(files, what, urlpath=pathlib.Path("/"), id=None, replace="", level=0):
  for file, deps in files.items():
    print(f"{'-'*level}Start {file.relative_to(basepath/'json')}")
    if id is False:
      print(f"-{'-'*level}Didn't get ID when supposed to", end="")
      if not fail:
        print("\nStopping because of setup error")
        sys.exit(67)
      else:
        print("... skipping")
        print(f"{'-'*level}End {file.relative_to(basepath/'json')}")
        continue
    with file.open(mode="r") as f:
      data = f.read()
    data = json.loads(data)
    if not isinstance(data, type({})):
      print(f"-{'-'*level}only dict in JSONs are supported", end="")
      if not fail:
        print("\nStopping because of setup error")
        sys.exit(67)
      else:
        print("... skipping")
        print(f"{'-'*level}End {file.relative_to(basepath/'json')}")
        continue
    urlpath = file.parent.relative_to(basepath/'json'/what)
    if id:
      urlpath = pathlib.Path(str(urlpath).replace(f"/{replace}/", f"/{id}/"))
    file_api_endpoint = API_ENDPOINT+str(urlpath)
    err, get_data = get(file_api_endpoint, file, level+1)
    if err:
      if not fail:
        print("\nStopping because of setup error")
        sys.exit(67)
      else:
        print("... skipping")
        print(f"{'-'*level}End {file.relative_to(basepath/'json')}")
        continue
    if err is None:
      idt = None
      idn = None
    else:
      idn = False
      err, idt = check_title(get_data, file, file.parent.name)
    if not remove:
      stream_check = False
      if isinstance(get_data, type({})):
        if get_data.get("message", "")\
            == "No pipeline connections with for stream to_stream":
          stream_check = True
      if err is not None or stream_check:
        if err is False or stream_check:
          if "date_setup" in data.keys():
            data = date_setup(data)
          if data is None:
            print(f"-{'-'*level}Couldn't process date_setup", end="")
            if not fail:
              print("\nStopping because of setup error")
              sys.exit(67)
            else:
              print("... skipping")
              print(f"{'-'*level}End {file.relative_to(basepath/'json')}")
              continue
          if "id_setup" in data.keys():
            data = id_setup(data, file, level)
          if data is None:
            print(f"-{'-'*level}Couldn't process id_setup", end="")
            if not fail:
              print("\nStopping because of setup error")
              sys.exit(67)
            else:
              print("... skipping")
              print(f"{'-'*level}End {file.relative_to(basepath/'json')}")
              continue
          idn = post(file_api_endpoint, file, data, level+1)
          if idn is None:
            print(f"-{'-'*level}Couldn't check ID for "
                  f"{file.relative_to(basepath/'json')}")
          if idn is not None and file.parent.name == "streams":
            post(file_api_endpoint+"/"+str(idn)+"/resume", file, None, level+1)
        else:
          print(f"-{'-'*level}Couldn't set {file.relative_to(basepath/'json')}, already "
                "exists")
      else:
        print(f"-{'-'*level}Couldn't set {file.relative_to(basepath/'json')}, "
              "invalid response", end="")
        if not fail:
          print("\nStopping because of setup error")
          sys.exit(67)
        else:
          print("... skipping")
          print(f"{'-'*level}End {file.relative_to(basepath/'json')}")
          continue
      if deps is not None:
        print(f"-{'-'*level}Trying dependants")
        if idt or idn:
          do_what(deps, what, urlpath, idt if idt else idn, file.stem, level=level+1)
        elif id is None:
          do_what(deps, what, urlpath, None, level=level+1)
        else:
          do_what(deps, what, urlpath, False, level=level+1)
    else:
      if not idt:
        print(f"-{'-'*level}Couldn't check ID for "
              f"{file.relative_to(basepath/'json')}")
      else:
        delete(file_api_endpoint, file, idt, level+1)
    print(f"{'-'*level}End {file.relative_to(basepath/'json')}")

def setup():
  if not elements:
    print("No elements specified, exiting...")
    sys.exit(66)
  lacking = []
  todo = []
  path = basepath/"json"
  for what in elements:
    lack = True
    for dirp in path.iterdir():
      if str(dirp.name).startswith(what) and dirp.is_dir():
        todo.append(dirp.name)
        lack = False
    if lack:
      lacking.append(what)
  if lacking:
    print("Couldn't find provided elements:\n"+"\n".join(lacking))
    sys.exit(66)
  if remove:
    todo.sort(reverse=True)
  else:
    todo.sort()
  for dirn in todo:
    files = get_file_dependants(path/dirn)
    print(f"Start {dirn}")
    do_what(files, dirn, level=1)
    print(f"End {dirn}")

if __name__ == "__main__":
  setup()
