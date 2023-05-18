#!/usr/bin/env python3
import os
import re
import sys
import copy
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
  "JSONs are data sent to those API endpoints.",
  epilog="Error codes: "
       "65 - unsupported interpreter version\n66 - config file errors"
       "67 - Graylog setup error")
parser.add_argument(
  "elements", nargs="*",
  help="element names")
parser.add_argument(
  "-i", "--ignore", dest="ignore", nargs="*",
  help="ignore files (parses given string as regex with path "
       "relative to 'json' dir)")
parser.add_argument(
  "-l", "--list", dest="list", action="store_true",
  help="list detected elements")
parser.add_argument(
  "-f", "--no-fail", dest="fail", action="store_false",
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
  "-v", "--verbose", dest="verbose", action='count', default=0,
  help="show more info")
args = parser.parse_args()

detected_elements = [i.name for i in pathlib.Path("json").iterdir() if\
                      i.is_dir()]
sorted(detected_elements)
if args.list:
  print("Detected elements:\n"+"".join(detected_elements))
  sys.exit(0)

elements = args.elements
ignore = args.ignore
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

def check_one(data, filedata, fields, searched):
  for key, value in fields.items():
    if data.get(key, None) != filedata.get(value, None):
      return
  else:
    return data.get(searched, None)

def find_list_index(data, conditions={}):
  if type(data) != type([]):
    data = [data]
  for i, ls in enumerate(data):
    for key, value in conditions.items():
      if ls.get(key) != value:
        break
    else:
      return i

def check_dict(data, field):
  answer = data
  for i in field.split("/"):
    answer = answer.get(i, None)
  return answer

def add_timestamp(data, setup):
  if not isinstance(setup, type([])):
    return
  for i in setup:
    now = datetime.datetime.utcnow()
    now = now.strftime('%Y-%m-%dT%H:%M:%S.%f+00:00')
    data = replace_nested_dict(data, i.split("/"), now)
  return data

def verbose_request(endpoint, response, response_type, settings, data=None):
  print(f"{response_type} API endpoint: {API_ENDPOINT+endpoint}")
  print("Response code:", response.status_code, response.reason)
  print(f"JSON sent: \n{data}")
  print(f"JSON received: \n{response.json() if response.text else None}")
  print(f"JSON settings: \n{settings}")

def get(file, settings, dirn, entry, important=True):
  code = settings.get("code", 200)
  if type(code) != type([]):
    code = [code]
  response = requests.get(
    API_ENDPOINT+settings.get("endpoint"),
    headers=HEADERS,
    auth=AUTH,
  )
  if verbose > 1:
    verbose_request(settings.get("endpoint"), response, "GET", settings)
  err = False
  if response.status_code not in code:
    if verbose == 1:
      verbose_request(settings.get("endpoint"), response, "GET", settings)
    print(f"{dirn}:{entry}:{file.relative_to(basepath/'json'/dirn)} "
          "couldn't process GET")
    if fail or important:
      print("Stopping because of Graylog setup error")
      sys.exit(67)
    print("Skipping GET...")
    err = True
  return response.json() if response.text else {}, err

def put(file, settings, data, dirn, entry):
  code = settings.get("code", [200, 201, 204])
  if type(code) != type([]):
    code = [code]
  response = requests.put(
    API_ENDPOINT+settings.get("endpoint"),
    headers=HEADERS,
    json=data,
    auth=AUTH,
  )
  if verbose > 1:
    verbose_request(settings.get("endpoint"), response, "PUT", settings, data)
  if response.status_code not in code:
    if verbose == 1:
      verbose_request(settings.get("endpoint"), response, "PUT", settings, data)
    print(f"{dirn}:{entry}:{file.relative_to(basepath/'json'/dirn)} "
          "couldn't process PUT")
    if fail:
      print("Stopping because of Graylog setup error")
      sys.exit(67)
    else:
      print("Skipping PUT...")
  else:
    print(f"{dirn}:{entry}:{file.relative_to(basepath/'json'/dirn)}"
          " PUT ended successfully")
  return response.json() if response.text else {}

def post(file, settings, data, dirn, entry):
  code = settings.get("code", [200, 201, 204])
  if type(code) != type([]):
    code = [code]
  response = requests.post(
    API_ENDPOINT+settings.get("endpoint"),
    headers=HEADERS,
    json=data,
    auth=AUTH,
  )
  if verbose > 1:
    verbose_request(settings.get("endpoint"), response, "POST", settings, data)
  if response.status_code not in code:
    if verbose == 1:
      verbose_request(settings.get("endpoint"), response, "POST", settings,
                      data)
    print(f"{dirn}:{entry}:{file.relative_to(basepath/'json'/dirn)} "
          "couldn't process POST")
    if fail:
      print("Stopping because of Graylog setup error")
      sys.exit(67)
    else:
      print("Skipping POST...")
  else:
    print(f"{dirn}:{entry}:{file.relative_to(basepath/'json'/dirn)}"
          " POST ended successfully")
  return response.json() if response.text else {}

def delete(file, settings, idt, dirn, entry):
  code = [200, 201, 204]
  if idt:
    response = requests.delete(
      API_ENDPOINT+settings.get("endpoint")+f"/{idt}",
      headers=HEADERS,
      auth=AUTH,
    )
    if verbose > 1:
      verbose_request(settings.get("endpoint")+f"/{idt}", response, "DELETE", settings)
    if response.status_code in code:
      print(f"{dirn}:{entry}:{file.relative_to(basepath/'json'/dirn)} "
            "DELETE successful")
    elif response.status_code == 404:
      if verbose == 1:
        verbose_request(settings.get("endpoint")+f"/{idt}", response, "DELETE", settings)
      print(f"{dirn}:{entry}:{file.relative_to(basepath/'json'/dirn)} "
            "couldn't DELETE, endpoint does not exist")
    else:
      if verbose == 1:
        verbose_request(settings.get("endpoint")+f"/{idt}", response, "DELETE", settings)
      print(f"{dirn}:{entry}:{file.relative_to(basepath/'json'/dirn)} "
            "couldn't process DELETE")
      if fail:
        print("Stopping because of Graylog setup error")
        sys.exit(67)
    return response.json() if response.text else {}
  else:
    print(f"{dirn}:{entry}:{file.relative_to(basepath/'json'/dirn)} "
          "couldn't DELETE, endpoint does not exist")

def fetch_replace(file, settings, data, dirn, entry):
  if not data:
    replacement_list = settings.get("endpoint_fetch_replace")
  else:
    replacement_list = settings.get("file_fetch_replace")
  if replacement_list is None:
    return settings
  for field, field_settings in replacement_list.items():
    get_data, err = get(file, field_settings, dirn, entry)
    if err:
      return
    search_path = field_settings.get("search_key")
    answer = get_data
    for spath in search_path.split("/"):
      if answer is None:
        return
      if spath != " ":
        answer = answer.get(spath)
      else:
        conditions = field_settings.get("search_conditions", {})
        index = find_list_index(answer, conditions)
        if index is None:
          return
        answer = answer[index]
    if not data:
      settings["endpoint"] = settings["endpoint"].replace(f"/{field}/",
                                                          f"/{answer}/")
    else:
      temp = replace_nested_dict(data, [field], answer,
                                 field_settings.get("is_list", False))
      if temp is None:
        if verbose > 1:
          print("Replaced data:", data)
        print(f"{dirn}:{entry}:{file.relative_to(basepath/'json'/dirn)} "
              "couldn't do file_fetch_replace "
              "Stopping because of config error")
        sys.exit(67)
      data = temp
  if data:
    return data
  else:
    return settings

def env_replace(file, settings, data, dirn, entry):
  replacement_list = settings.get("file_env_replace")
  for key, env in replacement_list:
    var = os.getenv(env)
    if var is not None:
      temp = replace_nested_dict(data, key.split("/"), var)
      if temp is None:
        if verbose > 1:
          print("Replaced data:", data)
        print(f"{dirn}:{entry}:{file.relative_to(basepath/'json'/dirn)} "
              "couldn't do file_env_replace "
              "Stopping because of config error")
        sys.exit(67)
      data = temp
  return settings

def process_dir(dirn):
  config = get_config(dirn)
  entries = config.get("configs")
  elementdir = basepath/"json"/dirn
  if not entries:
    return
  entries = list(entries.items())
  if remove:
    entries.reverse()
  for entry, settings in entries:
    todo_files = []
    print(f"Start {dirn}:{entry}")
    location = settings.get("location", "NO_FILE")
    if settings.get("is_dir", False) and location != "NO_FILE":
      if not (elementdir/location).is_dir:
        print(f"{dirn}:{entry}:{location} is not directory "
              "as stated in config file! \n"
              "Stopping because of config error")
        sys.exit(67)
      else:
        for file in (elementdir/location).glob("*.json"):
          if not file.is_dir():
            todo_files.append(file)
    else:
      file = elementdir/location
      if not str(file).endswith(".json") and location != "NO_FILE":
        file = pathlib.Path(str(file)+".json")
      todo_files = [file]
    for file in todo_files:
      if ignore:
        ign = False
        for i in ignore:
          if re.search(i, str(file.relative_to(basepath/'json'))):
            print(f"Ignoring {dirn}:{entry}:{file.relative_to(basepath/'json'/dirn)}")
            ign = True
            break
        if ign:
          continue
      print(f"Start {dirn}:{entry}:{file.relative_to(basepath/'json'/dirn)}")
      file_settings = copy.deepcopy(settings)
      try:
        if not file_settings.get("deleteable", True) and remove:
          print(f"{dirn}:{entry}:{file.relative_to(basepath/'json'/dirn)} "
                "cannot be deleted as stated in file")
          print(f"End {dirn}:{entry}:{file.relative_to(basepath/'json'/dirn)}")
          continue
        if file_settings.get("endpoint_fetch_replace"):
          file_settings = fetch_replace(file, file_settings, None, dirn, entry)
          if file_settings is None:
            print(f"{dirn}:{entry}:{file.relative_to(basepath/'json'/dirn)}"
                  " endpoint fetch replacement not found.")
            if remove:
              print("Skipping DELETE...")
              print(f"End {dirn}:{entry}:{file.relative_to(basepath/'json'/dirn)}")
              continue
            else:
              print("Stopping because of config error")
              sys.exit(67)
        id = None
        if location != "NO_FILE":
          with file.open() as f:
            data = f.read()
            data = json.loads(data)
          if not remove:
            if file_settings.get("file_fetch_replace"):
              data = fetch_replace(file, file_settings, data, dirn, entry)
              if data is None:
                print(f"{dirn}:{entry}:{file.relative_to(basepath/'json'/dirn)} "
                      "file fetch replacement not found.")
                if remove:
                  print("Skipping DELETE...")
                  print(f"End {dirn}:{entry}:{file.relative_to(basepath/'json'/dirn)}")
                  continue
                else:
                  print("Stopping because of config error")
                  sys.exit(67)
            if file_settings.get("file_env_replace"):
              data = env_replace(file, file_settings, data, dirn, entry)
            if file_settings.get("add_timestamp"):
              data = add_timestamp(data, file_settings.get("add_timestamp"))
            if data is None:
              raise TypeError
          if file_settings.get("check_if_exists", True) or remove:
            where = file_settings.get("endpoint").split("/")[-1]
            search = file_settings.get("identifier", "title")
            search_value = data[search]
            get_data, err = get(file, file_settings, dirn, entry, False)
            if not err:
              if type(get_data) == type([]):
                err = True
                index = find_list_index(get_data, {search: search_value})
                if index is not None:
                  err = False
                  get_data = get_data[index]
              if not err:
                if type(get_data) == type({}):
                  err = True
                  if get_data.get(where):
                    get_data = get_data.get(where)
                    err = False
                  elif get_data.get("id"):
                    get_data = get_data.get("id")
                    err = False
                if not err:
                  if type(get_data) not in (type([]), type({})):
                    id = get_data
                  else:
                    if type(get_data) == type([]):
                      err = True
                      index = find_list_index(get_data, {search: search_value})
                      if index is not None:
                        get_data = get_data[index]
                        err = False
                      if not err:
                        id = check_dict(get_data, "id")
        else:
          data = None
      except TypeError:
        print(f"{dirn}:{entry}:{file.relative_to(basepath/'json'/dirn)} "
              "is invalid! Check config and associated JSONs."
              "Stopping because of config error")
        sys.exit(67)
      if remove and file_settings.get("method", "POST") == "POST":
        if id is None:
          print(f"{dirn}:{entry}:{file.relative_to(basepath/'json'/dirn)} "
                "couldn't be found in fetched data.\n"
                "Skipping DELETE...")
          print(f"End {dirn}:{entry}:{file.relative_to(basepath/'json'/dirn)}")
          continue
        delete(file, file_settings, id, dirn, entry)
      else:
        if file_settings.get("method", "POST") == "PUT":
          if id is not None:
            put(file, file_settings, data, dirn, entry)
          else:
            print(f"{dirn}:{entry}:{file.relative_to(basepath/'json'/dirn)} "
                  "found in fetched data. PUT failed.")
            if fail:
              print("Stopping because of Graylog setup error")
              sys.exit(67)
            else:
              print("Skipping PUT...")
              print(f"End {dirn}:{entry}:{file.relative_to(basepath/'json'/dirn)}")
              continue
        else:
          if id is None:
            post(file, file_settings, data, dirn, entry)
          else:
            print(f"{dirn}:{entry}:{file.relative_to(basepath/'json'/dirn)} "
                  "found in fetched data. POST failed.")
            if fail:
              print("Stopping because of Graylog setup error")
              sys.exit(67)
            else:
              print("Skipping POST...")
              print(f"End {dirn}:{entry}:{file.relative_to(basepath/'json'/dirn)}")
              continue
      print(f"End {dirn}:{entry}:{file.relative_to(basepath/'json'/dirn)}")
    print(f"End {dirn}:{entry}")

def get_config(dirn, name=""):
  try:
    with open("json/"+dirn+"/config.json") as f:
      data = f.read()
  except FileNotFoundError:
    print(f"Couldn't find config.json in json/{dirn}, required by "
          f"{name if name else 'user input'}, exiting...")
    sys.exit(66)
  try:
    return json.loads(data)
  except json.decoder.JSONDecodeError as e:
    print(e)
    print(f"config.json in json/{dirn} is invalid, required by "
          f"{name if name else 'user input'}, exiting...")
    sys.exit(66)

def check_dirs(dirs, todo=[], path=pathlib.Path(), pdirn=""):
  for dirn in dirs:
    config = check_dict(get_config(dirn, pdirn), "depends_on")
    if config:
      ctodo = check_dirs(config, todo, path, dirn)
      for i in ctodo:
        if i not in todo:
          todo.append(i)
    if dirn not in todo:
      todo.append(dirn)
  return todo

def setup():
  if not elements:
    print("No elements specified, exiting...")
    sys.exit(66)
  path = basepath/"json"
  todo = check_dirs(elements, path=path)
  if remove:
    todo.sort(reverse=True)
  else:
    todo.sort()
  for dirn in todo:
    print(f"Start {dirn}")
    process_dir(dirn)
    print(f"End {dirn}")

if __name__ == "__main__":
  setup()
