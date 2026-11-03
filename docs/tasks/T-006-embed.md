# T-006: Встраивание в витрину

**Цель:** EMB-1…EMB-6, NFR-4.
**Данные:** `v5/test_data/token_test_vectors.json`.
**Файлы:** `app/services/token.py`, `app/web/embed.py`, `app/templates/embed/*`, заголовки CSP/CORS в `app/main.py`, `.env.example` (`PX_SECRET`), тесты.
**Критерии приёмки:**
- Страница витрины открывает конфигуратор в iframe; `partner_id` из токена; ручного ввода нет.
- Мусорный и истёкший токен → страница ошибки, обращений в БД с валидным `partner_id` нет (V5 A2, A3).
- `postMessage({type:'qod:export', payload})` принимается витриной только со своего origin; порт 0 и протокол FTP отклоняются до отправки.
- CSP `frame-ancestors`; фолбэк «в новой вкладке».
- Решить вопрос EMB-6 (один процесс или два origin) по analysis §7 п.3.
**Зависит от:** T-005
**Журнал:**
