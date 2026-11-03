# Исходные материалы задания

Первоисточники. **Не редактировать.** Требования в `docs/requirements.md` ссылаются на них по меткам.
Получено: 2026-11-03.

| Метка | Файл | Что это |
|---|---|---|
| **[T]** | `01-task-qos-partner-services-v5.pdf` | Задание (v5): шаги 3–8, flow-диаграмма на стр. 5, требования |
| **[F]** | `02-team-feedback-qos-platform.pdf` | HLD QoD, граница CAMARA/3GPP, UC-лист PoC (слайд 13), открытые вопросы (слайд 16) |
| **[M]** | `03-mvp-guidance.md` | Рекомендации по MVP и пересказ задачи заказчиком |
| **[S]** | `zadanie/О_проекте_простыми_словами.md` | Суть проекта без жаргона, словарь, справочник профилей |
| **[V1]…[V5]** | `zadanie/tz/variant_N_*/ТЗ.md` + `test_data/` | Пять вариантов ТЗ на 3 часа: CRUD-инвентори, schema-driven, AI-агент, песочница, витрина PX + iframe. Каждый с сидами, эталонами и сценариями. Обзор — `zadanie/tz/README.md` |
| **[3G]** | `zadanie/TS29122_AsSessionWithQoS.yaml`, `zadanie/TS29122_PfdManagement.yaml` | 3GPP TS 29.122: интерфейс T8 (SCEF/NEF) — QoS-сессия приложения и управление PFD (описание трафика приложения) |
| **[CP]** | `camara/qos-profiles.yaml` | CAMARA QoS Profiles (main) |
| **[CQ]** | `camara/quality-on-demand.yaml` | CAMARA Quality-on-Demand: сессии (релиз r3.2, снимок main) |
| **[CA]** | `camara/qos-provisioning.yaml` | CAMARA QoS Provisioning: бессрочное назначение профиля устройству |

## Снимок CAMARA
Скачан с `raw.githubusercontent.com/camaraproject/…/main/code/API_definitions/`.
Коммиты на 2026-10-30: QoSProfiles `a6f5dfaa7eb3`, QualityOnDemand `ae1c5178b98c`. В файлах `version: wip`; последний релиз QoD — r3.2 (2025-09-16). Лицензия Apache-2.0. Обновлять только осознанно: на этих файлах строятся требования.

## Внешние ссылки из PDF
Confluence МТС (`confluence.mts.ru`) из нашей среды **недоступен** (ошибка SSL-сертификата), содержимое не читалось.

- Qos platform prototype v.01 — `confluence.mts.ru/display/~avvedin2/Qos+platform+prototype+v.01` (этапы 1–8)
- Архитектура QoD, QoD API, QoD детали, 3GPP AsSessionWithQoS vs CAMARA QoD — `confluence.mts.ru`, pageId 2648025168, 2649070825, 2647760200, 2649068922, 2649069502
- Полное ТЗ кейса и сводный анализ вариантов — на них ссылается `zadanie/tz/README.md`, в нашей копии их нет
- GSMA OPG.13 — https://www.gsma.com/solutions-and-impact/technologies/networks/gsma_resources/opg13-implementing-tm-forum-operate-apis/
- TM Forum × CAMARA — https://www.tmforum.org/oda/open-apis/partners/camara
- Vodafone — https://developer.vodafone.com/camara
- Orange TMF931 — https://docs.developer.orange.com/network-apis/api-catalog/tmf931-onboarding-and-ordering/ww/current/getting-started

## Ожидается от заказчика
Официальная спецификация JSON для PX — стандарта нет, на время работаем по нашему предложению `docs/px-json-proposal.md` (на основе примера `expected_export.json`, V1/V2/V3). Справочник сигнатур систем коммутации. Дополнительные материалы — обещаны.
