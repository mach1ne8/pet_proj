# Публикация сайта

`npm run dev -- --host 0.0.0.0` запускает сервер разработки Vite. Для
публичного сайта Nginx должен отдавать результат `npm run build`, а `/api/`
проксировать к FastAPI на `127.0.0.1:8000`. PostgreSQL уже привязан к
`127.0.0.1:5432` в `docker-compose.yml`.

Конфигурация [nginx/negotiation-arena.conf](nginx/negotiation-arena.conf)
перенаправляет HTTP на HTTPS-имя K2 и предусматривает:

- статические файлы из `/var/www/negotiation-arena` и SPA-маршруты;
- лимиты на запросы с одного IP: 20/с для сайта, 10/с для API, 1/с для
  `POST`/`PATCH` API (с короткими всплесками до 100/100/60 соответственно);
- общий лимит API 50/с и не более 128 одновременно обрабатываемых запросов;
- общий лимит `POST`/`PATCH` API 2/с со всплеском 100 и не более 64 таких
  запросов одновременно: около 50 посетителей могут почти одновременно
  открыть страницу и создать игровую сессию;
- не более 10 одновременно обрабатываемых запросов, ожидающих синхронный
  ответ Ollama (`/api/chat` и `/api/sessions/{id}/suggest`); лишние получают
  `429`. Ollama запускает до 4 генераций параллельно, остальные ждут её
  очередь. Для этого на ВМ установлен `LLM_TIMEOUT_SECONDS=120`, а таймаут
  ожидания ответа прокси равен 180 секундам;
- максимум 64 одновременно обрабатываемых запроса с одного IP, код `429`
  при превышении лимитов и ограничение тела запроса до 32 КБ;
- передачу `/api/` только на локальный FastAPI.

Лимиты ориентированы на 20–50 посетителей, которые просматривают сайт и
отправляют сообщения в разное время. После увеличения ВМ до 12 vCPU и 24 ГБ
RAM повторный прогон 10 одновременных игровых сообщений через HTTPS/Nginx
дал 10 ответов `200` за 22–74 секунды. Это один тест с коротким сообщением
и началом диалога, а не гарантия времени ответа для длинных игр или
дополнительных фоновых LLM-задач. Для большего числа одновременных игровых
запросов понадобится ускорять инференс и/или вынести ожидание в фоновую
очередь с выдачей результата через опрос. После публикации проверьте логи
и настройте лимиты под реальную нагрузку, особенно если несколько людей
выходят через один NAT. Публичный API пока не требует авторизации:
боты могут создавать сессии и запускать LLM-вызовы. Лимит по IP уменьшает
нагрузку от одного источника, но не останавливает распределённую атаку.

## Развёртывание на ВМ

На текущей ВМ Nginx, Certbot, сертификат и systemd-сервис API уже установлены. Следующие команды
показывают порядок повторного развёртывания **на самой ВМ** из корня
репозитория. Убедитесь, что FastAPI запущен без `--reload` и слушает только
`127.0.0.1:8000`. Перед выпуском сертификата TCP 80 должен быть доступен
снаружи, а имя `c2-217-73-57-48.elastic.k2.cloud` должно указывать на IP ВМ.

```bash
sudo apt install nginx certbot
npm ci
npm run build
sudo install -d -m 0755 /var/www/negotiation-arena
sudo cp -a dist/. /var/www/negotiation-arena/
sudo install -m 0644 deploy/nginx/negotiation-arena-http-bootstrap.conf /etc/nginx/conf.d/negotiation-arena.conf
sudo nginx -t
sudo systemctl enable --now nginx
sudo systemctl reload nginx
sudo certbot certonly --webroot --webroot-path /var/www/negotiation-arena --domain c2-217-73-57-48.elastic.k2.cloud --email YOUR_EMAIL --agree-tos --non-interactive
sudo install -m 0644 deploy/nginx/negotiation-arena.conf /etc/nginx/conf.d/negotiation-arena.conf
sudo install -d -m 0755 /etc/letsencrypt/renewal-hooks/deploy
sudo install -m 0755 deploy/certbot/reload-nginx.sh /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh
sudo nginx -t
sudo systemctl reload nginx
sudo certbot renew --dry-run --no-random-sleep-on-renew
curl --noproxy '*' -I http://127.0.0.1/
curl --noproxy '*' --resolve c2-217-73-57-48.elastic.k2.cloud:443:127.0.0.1 -I https://c2-217-73-57-48.elastic.k2.cloud/
```

FastAPI запускается сервисом [systemd/negotiation-arena-api.service](systemd/negotiation-arena-api.service).
При повторном развёртывании после установки Python-зависимостей и миграций:

```bash
sudo install -m 0644 deploy/systemd/negotiation-arena-api.service /etc/systemd/system/negotiation-arena-api.service
sudo systemctl daemon-reload
sudo systemctl enable --now negotiation-arena-api.service
curl --noproxy '*' http://127.0.0.1:8000/health
```

Локальная модель Ollama использует четыре параллельные генерации благодаря
[systemd/ollama-parallel.conf](systemd/ollama-parallel.conf). Для повторного
применения настройки на ВМ:

```bash
sudo install -d -m 0755 /etc/systemd/system/ollama.service.d
sudo install -m 0644 deploy/systemd/ollama-parallel.conf /etc/systemd/system/ollama.service.d/parallel.conf
sudo systemctl daemon-reload
sudo systemctl restart ollama
systemctl show ollama -p Environment
```

Для текущей CPU-модели в корневом `.env` установлено
`LLM_TIMEOUT_SECONDS=120`. После его изменения перезапустите
`negotiation-arena-api.service`. Этот таймаут и `proxy_read_timeout` Nginx
должны оставаться согласованными.

В Fedora/RHEL с SELinux после копирования статики может понадобиться
`sudo restorecon -RF /var/www/negotiation-arena`. Если Nginx отвечает `502`,
сначала проверьте FastAPI на `127.0.0.1:8000` и журнал Nginx; если причина
именно в запрете SELinux на соединение к API, настройте доступ Nginx к
локальному upstream (например, `httpd_can_network_connect`).

Если `nginx -t` сообщает о повторном `default_server` на порту 80, проверьте
установленный по умолчанию `server` в `/etc/nginx/nginx.conf` или
`sites-enabled/default` и отключите его перед повторной проверкой. Не
перезапускайте Nginx с ошибочной конфигурацией. После проверки замените
`nohup npm run dev -- --host 0.0.0.0`: Vite больше не нужен для отдачи сайта.
Закройте входящий 5173 в облачном firewall. Входящие 8000, 5432 и порт LLM
также должны быть закрыты извне. Сохраните SSH-доступ при изменении правил.

## Публикация в K2 Cloud без внешней защиты

Добавьте в [группе безопасности](https://docs.k2.cloud/ru/services/security/securitygroups.html)
входящие правила **TCP 80 и TCP 443 от 0.0.0.0/0**. Порты 5173, 8000,
5432 и 11434 для всех не открывайте. Проверьте
`https://c2-217-73-57-48.elastic.k2.cloud/` из внешней сети; запрос к
`http://217.73.57.48/` должен перенаправлять на HTTPS. После перехода
закройте 5173 и остановите Vite dev server.

Сертификат выпущен на доменное имя, которое K2 назначил этому Elastic IP.
Certbot автоматически обновляет его через `certbot.timer`, а hook
[certbot/reload-nginx.sh](certbot/reload-nginx.sh) перезагружает Nginx после
успешного продления. Если IP изменится, обновите DNS-имя и сертификат в
конфигурации. HTTPS непосредственно на IP также [возможен](https://letsencrypt.org/2026/03/11/shorter-certs-certbot/),
но требует Certbot 5.4+ и шестидневного сертификата.

Лимиты Nginx сдерживают запросы к приложению и ограничивают суммарную нагрузку
на дорогие API-вызовы. Они работают после поступления трафика на ВМ: при
атаке, которая переполнит её сетевой канал, локальная настройка не сможет
сохранить доступность сайта. Следите за журналами и расходом трафика.

Из внешней сети убедитесь, что доступны только ожидаемые публичные порты.
Для диагностики лимитов смотрите `/var/log/nginx/error.log` и ответы `429`.
