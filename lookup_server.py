#!/usr/bin/env python3
from fastapi import FastAPI, Request

lookup = {}

app = FastAPI()

@app.get("/")
async def root(request: Request, key: str):
  delimeter = request.headers.get("actually-post-with-delimeter", "")
  delete = request.headers.get("actually-delete", None)
  if delete:
    try:
      del lookup[key]
      return True
    except KeyError:
      return None
  if not delimeter or (delimeter and delimeter not in key):
    if not key:
      return lookup
    else:
      return lookup.get(key, None)
  else:
    keylist = key.split(delimeter)
    key = keylist[0]
    keylist.pop(0)
    if lookup.get(key, None) is None:
      lookup[key] = {}
    if len(keylist) > 1:
      lookup[key]["list"] = keylist
    else:
      lookup[key]["value"] = keylist[0]
    return lookup.get(key)

if __name__ == "__main__":
  import re
  import subprocess
  import uvicorn
  result = subprocess.run(['ip', 'addr', 'show', 'docker0'], capture_output=True, text=True)
  ip_pattern = r'inet\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
  match = re.search(ip_pattern, result.stdout)
  if match:
    ip_address = match.group(1)
  else:
    ip_address = "0.0.0.0"
  uvicorn.run(app, host=ip_address, port=8000)
