# [PL] Repozytorium projektu inżynierskiego System agregacji logów w rozproszonym środowisku sieci 5G
# [EN] Project Repository for Engineering Thesis: Log Aggregation System in Distributed 5G Network Environment
## Purpose of Files and Directories
### docker-compose.yml
Enables running a test environment of Graylog, created using [documentation](https://go2docs.graylog.org/5-0/downloading_and_installing_graylog/docker_installation.htm#Configuration). The ports exposed on the host are 9000/tcp (REST API and web interface) and 1514/tcp (for syslog).
### json
Contains directories (sets) which subdirectories are API endpoints, and .json files are data to send.
### start.sh
Installs requests library, also allows to be sourced.
### setup_graylog.py
Script which sets up Graylog instance.
### lookup_server.py
Needs to be running to make pipeline rules processing multiple messages work. Holds temporary message data.
