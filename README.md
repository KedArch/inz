# [PL] Repozytorium projektu inżynierskiego System agregacji logów w rozproszonym środowisku sieci 5G
# [EN] Project Repository for Engineering Thesis: Log Aggregation System in Distributed 5G Network Environment

## Purpose of Files and Directories

### docker-compose.yml

Enables running a test environment of Graylog, created using [documentation](https://go2docs.graylog.org/5-0/downloading_and_installing_graylog/docker_installation.htm#Configuration). The ports exposed on the host are 9000/tcp (REST API and web interface) and 1514/tcp (for syslog).

### setup_content_pack.sh

Creates a Python virtual environment and runs install_content_pack.py.

### install_content_pack.py

Creates a content pack in Graylog from the content_pack.json file.
