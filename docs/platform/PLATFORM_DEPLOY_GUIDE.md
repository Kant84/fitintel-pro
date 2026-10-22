
---
## Дополнение от 22.10 (после боевой установки)
- **Отзыв сертификата**: вместо openssl ca -revoke (падает с Error creating serial number index на сертификатах, выпущенных через openssl x509) писать в index.txt напрямую строку со статусом R: printf \"R\\t<expiry>\\t<дата_отзыва_yyMMddHHmmssZ>\\t<serial>\\tunknown\\t/CN=<email>\" >> index.txt, затем openssl ca -gencrl и restart nginx. В index.txt не должно быть дублей серийника.
- **Порт WireGuard платформы**: если на сервере уже есть WG (наш кейс: контейнер wireguard-hub на 51820), платформе назначаем другой внешний порт (51829): sed замены в docker-compose.yml (порт публикации + SERVERPORT) + проброс UDP 51829 на роутере. Все peer-конфиги платформы автоматически получат Endpoint <IP>:51829.
