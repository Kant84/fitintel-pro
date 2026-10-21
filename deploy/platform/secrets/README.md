# Секреты платформы (НЕ коммитить)

- `license_private.key` — приватный ключ License Studio (Ed25519). Кладётся сюда перед
  `docker compose up` на этапе Б и подключается как Docker secret. В git не попадает
  (см. .gitignore). Держите копию в менеджере паролей.
