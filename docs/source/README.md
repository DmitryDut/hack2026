# Исходные материалы задания

Первоисточники. **Не редактировать.** Все требования в `docs/requirements.md` ссылаются на них.

| Файл | Исходное название | Что это |
|---|---|---|
| `01-task-qos-partner-services-v5.pdf` | «Создание прототипа процесса управления сервисами партнера в рамках хакатона 03.10.2026» (v5, экспорт 03.11.2026) | Само задание: шаги 3–8 процесса, требования, flow-диаграмма (стр. 5) |
| `02-team-feedback-qos-platform.pdf` | «QoS-платформа — preliminary team feedback» (19.10.2026, обновление 16.10.2026) | HLD QoD, граница решения CAMARA/3GPP, UC-лист PoC (слайд 13), открытые вопросы (слайд 16) |

Получено: 2026-11-03.

## Внешние ссылки из документов
Confluence МТС (`confluence.mts.ru`) из нашей среды **недоступен** (ошибка SSL-сертификата), содержимое не читалось.

- Qos platform prototype v.01 — `confluence.mts.ru/display/~avvedin2/Qos+platform+prototype+v.01` (родительское описание, этапы 1–8)
- Архитектура QoD, QoD API, QoD детали, 3GPP AsSessionWithQoS vs CAMARA QoD — `confluence.mts.ru`, pageId 2648025168, 2649070825, 2647760200, 2649068922, 2649069502
- GSMA OPG.13 — https://www.gsma.com/solutions-and-impact/technologies/networks/gsma_resources/opg13-implementing-tm-forum-operate-apis/
- TM Forum × CAMARA — https://www.tmforum.org/oda/open-apis/partners/camara
- Vodafone — https://developer.vodafone.com/camara
- Orange TMF931 — https://docs.developer.orange.com/network-apis/api-catalog/tmf931-onboarding-and-ordering/ww/current/getting-started
- Материалы по session flow — `confluence.mts.ru/display/~nmarkin/GSMA+QoD`

## Ожидаются от заказчика (в документах сказано «будет предоставлена спецификация»)
1. Справочник сигнатур / систем коммутации.
2. Спецификация QoS-профилей и Duration (для GSMA APIgw / CAMARA).
3. Спецификация JSON, который отдаётся в PX.
