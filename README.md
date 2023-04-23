# inz
Repozytorium projektu inżynierskiego System agregacji logów w rozproszonym środowisku sieci 5G
# Przeznaczenie plików i katalogów
## docker-compose.yml
Pozwala uruchomić testowe środowisko Graylog, utworzone przy pomocy [dokumentacji](https://go2docs.graylog.org/5-0/downloading_and_installing_graylog/docker_installation.htm#Configuration). Wystawione na hoście są porty 9000/tcp (REST API i strona przeglądarkowa) oraz 1514/tcp (do syslog).
## setup_content_pack.sh
Tworzy środowisko wirtualne Pythona i uruchamia install_content_pack.py
## install_content_pack.py
Tworzy w Graylogu content pack z pliku content_pack.json
