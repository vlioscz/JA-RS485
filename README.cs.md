<p align="center"><img src="brands/logo@2x.png" alt="JA-RS485" width="461"></p>

# JA-RS485 — Jablotron v Home Assistantu přes sběrnicové rozhraní JA-121T (RS-485)

[English](README.md) | **Čeština**

[![Validate](https://github.com/vlioscz/JA-RS485/actions/workflows/validate.yml/badge.svg)](https://github.com/vlioscz/JA-RS485/actions/workflows/validate.yml)
[![GitHub release](https://img.shields.io/github/v/release/vlioscz/JA-RS485)](https://github.com/vlioscz/JA-RS485/releases)
[![HACS](https://img.shields.io/badge/HACS-custom-orange.svg)](https://hacs.xyz)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Custom integrace pro Home Assistant — čtení a ovládání zabezpečovacího systému
**Jablotron JABLOTRON 100 / 100+** přes **[sběrnicové rozhraní JA-121T (RS-485)](https://portal.jablotron.com/cs/sbernicove-rozhrani-rs-485)**
(ASCII protokol, 9600 Bd, 8N1 — dle Jablotron manuálu MNN51111), typicky připojené USB↔RS-485 převodníkem.

## Proč zrovna RS-485? (srovnání s ostatními Jablotron integracemi)

Do Home Assistantu jde Jablotron dostat i jinak:

- **[Jablotron Cloud](https://github.com/Pigotka/ha-cc-jablotron-cloud)** — používá cloudové API
  MyJABLOTRON. Žádná kabeláž, ale závisí na tvém internetovém připojení *a* na dostupnosti
  Jablotron cloudu: když vypadne kterékoliv z toho, vypadne i alarm v HA.
- **[Jablotron 100](https://github.com/kukulich/home-assistant-jablotron100)** — připojuje se
  přímo do ústředny přes USB. Umí toho hodně, ale HA musí stát hned vedle ústředny, USB kabel
  může někdo omylem vytáhnout a na větší vzdálenost musíš řešit, jak USB prodloužit (na což
  nebylo nikdy stavěné).

Tato integrace možná nenabízí úplně všechny funkce těch dvou, zato je **nejhůř rozbitná**:
JA-121T komunikuje po vyhrazené sběrnici RS-485 — průmyslovém standardu navrženém na stovky
metrů obyčejné kroucené dvojlinky, s galvanickým oddělením a šroubovacími svorkami, které
nevypadnou. Všechno běží **čistě lokálně** (žádný internet, žádný cloudový účet), a kdyby
linka přece jen spadla, integrace se sama znovu připojí a dá ti o tom vědět
(`binary_sensor.jablotron_bus_connection`).

## Funkce

- **Alarm panel** (entita `alarm_control_panel`) pro každou sekci — zapnutí (SET), částečné
  zapnutí (SETP), vypnutí (UNSET), se správnými stavy HA: `disarmed`, `arming` (odchodové
  zpoždění), `pending` (příchodové zpoždění), `armed_away`, `armed_home` a `triggered`
  (poplach vloupání / požár / tíseň)
- **Switch** pro každý PG výstup (PGON / PGOFF), bez optimismu — stav se přepne až poté,
  co ho ústředna potvrdí. PG nakonfigurované v F-Linku jako **impuls** stačí uvést
  v nastavení a vytvoří se místo přepínače jako **tlačítko** (stisk = PGON)
- **Device triggery** — „Poplach vloupání / Požární / Tísňový / Jakýkoliv" (volitelně pro
  jednu sekci) vybereš přímo v UI editoru automatizací
- **Diagnostický sensor** pro každou sekci se surovým stavem JA-121T (`READY`, `ARMED`,
  `ARMED_PART`, `BLOCKED`, `SERVICE`, …) a aktivními příznaky v atributech
- **Binary sensor** pro každou periferii (čidlo) dekódovaný z bitmapy `PRFSTATE` — vytvoří se
  automaticky při první aktivaci, nebo vyber pozice explicitně v nastavení integrace (čísla
  odpovídají záložce Zařízení v F-Linku, 0 = ústředna). Pozn.: protokol nenese názvy ani typy
  čidel — entity si přejmenuj v HA
- **Filtr entit** v nastavení integrace — vyber, které sekce, PG výstupy a periferie se mají
  vytvářet jako entity (stavové dotazy nejsou omezené právy kódu, takže standardně je vidět
  vše, co ústředna hlásí)
- **Práva ovládání** v nastavení integrace, zrcadlící práva přístupového kódu z F-Linku:
  typ ovládání sekcí (plný / jen zakódovat / jen čtení), které sekce lze ovládat a zda/které
  PG výstupy lze ovládat. Zakázané povely se odmítnou lokálně se srozumitelnou chybou, místo
  aby se zkoušely proti ústředně (`NO_ACCESS` pokusy by zaplevelily historii událostí
  Jablotronu)
- Sekce a PG výstupy se **objevují automaticky** ze sběrnice (počáteční dotaz
  `STATE` / `PGSTATE` + spontánní hlášení); nové se přidají bez restartu
- **Push aktualizace** — změny sekcí a PG hlásí JA-121T okamžitě. Stavy čidel (PRFSTATE)
  ústředna vysílá jen cca každých 10 s, takže binary sensory čidel jsou **pouze
  informativní** — pro automatizace veď čidlo v F-Linku přes PG výstup (změny PG chodí
  okamžitě). Každých 5 minut běží plná resynchronizace stavů, která dožene cokoliv
  ztraceného kolizemi na poloduplexní lince
- **Automatický reconnect** s backoffem, když sériový port zmizí (např. přepojení USB);
  entity jsou mezitím `unavailable`
- Config flow ověří spojení i přístupový kód ještě před vytvořením záznamu;
  **Znovu nakonfigurovat** umožní později změnit port nebo kód bez ztráty entit
- Událost **`ja_rs485_alarm`** na sběrnici HA při každé změně poplachového příznaku sekce —
  ideální pro push notifikace
- **Binary sensor stavu spojení** (`binary_sensor.jablotron_bus_connection`) pro hlídání
  sériové linky
- **Diagnostika** ke stažení (přístupový kód začerněný) včetně posledních 50 přijatých řádků
  protokolu — přilož ji, když hlásíš problém
- Entity sekcí mají atribut `state_changed_at` (UTC) s časem poslední hlášené změny stavu

## Bezpečnostní poznámky

- Veškerá komunikace běží ve vyhrazeném vlákně — nic neblokuje event loop HA.
- Povely se skládají výhradně z validovaných čísel (sekce 1–15, PG 1–128); přístupový kód má
  omezenou znakovou sadu už při nastavení. Nic od uživatele nemůže na linku propašovat další
  příkazy.
- Přístupový kód je uložený v config entry HA a **nikdy se nezapisuje do logů**.
- **Vyhraď integraci samostatný uživatelský kód** jen s potřebnými právy (které sekce smí
  ovládat, které PG výstupy). Každý povel se zapisuje do historie událostí Jablotronu pod
  tímto uživatelem.
- Neúspěšné povely (např. `ERROR: 3 NO_ACCESS`) se logují a u zapnutí/vypnutí se chyba ukáže
  přímo v UI — nikdy se nepředstírá úspěch.

## Požadavky

- Home Assistant 2024.11 nebo novější
- JA-121T naučený v ústředně, režim **Terminál** (výchozí; nastavuje se v F-Linku →
  Vnitřní nastavení)
- USB↔RS-485 převodník (FTDI / CH340 / CP2102 — fungují všechny)

### Zapojení (dvě věci, které každý zkazí)

1. **Externí napájení 12 V je povinné.** RS-485 strana JA-121T je galvanicky oddělená
   a **nenapájí se** ze sběrnice Jablotronu. Přiveď **12 V DC** (dle manuálu 6–28 V) na
   svorky **+U/GND na výstupní (RS-485) straně**. Bez něj je na lince jen šum (ojedinělé
   rozbité bajty typu `\x00`).
2. **Polarita datových vodičů:** JA-121T **A → D+ převodníku**, **B → D−**, a propoj **GND**
   výstupní strany JA-121T se zemí převodníku. (Značení A/B u RS-485 není standardizované —
   pokud s připojeným napájením chodí jen smetí, prohoď A/B.)

## Instalace

### HACS (doporučeno)

1. **HACS → ⋮ → Vlastní repozitáře**, přidej `https://github.com/vlioscz/JA-RS485`
   jako typ **Integrace** (tento krok přeskoč, až bude repozitář ve výchozím HACS store).
2. Vyhledej v HACS **JA-RS485**, stáhni a restartuj Home Assistant.

### Ručně

1. Zkopíruj `custom_components/ja_rs485/` do `config/custom_components/ja_rs485/`.
2. Restartuj Home Assistant.

### Nastavení

1. **Nastavení → Zařízení a služby → Přidat integraci → JA-RS485.**
2. Vyber sériový port — radši stabilní cestu `/dev/serial/by-id/usb-...` než `/dev/ttyUSB0`
   (přežije restarty a přepojení) — a zadej přístupový kód (s prefixem, pokud jej systém
   používá, např. `1*1234`).

## Služby

Zachované pro zpětnou kompatibilitu a automatizace; preferovaná cesta jsou entity
alarmu/switche.

| Služba | Povel | Popis |
|--------|-------|-------|
| `ja_rs485.set_zone` | `SET n` | Zapne sekci (1–15) |
| `ja_rs485.set_zone_partial` | `SETP n` | Částečně zapne sekci |
| `ja_rs485.unset_zone` | `UNSET n` | Vypne sekci |
| `ja_rs485.pgon` | `PGON n` | Zapne PG výstup (1–128) |
| `ja_rs485.pgoff` | `PGOFF n` | Vypne PG výstup |

## Lovelace dashboard

`dashboards/jablotron_dashboard.yaml` automaticky vygeneruje dlaždice pro všechny sekce
(s tlačítky zapnout/vypnout) a PG výstupy. Potřebuje jen plugin
[auto-entities](https://github.com/thomasloven/lovelace-auto-entities) (HACS).

## Automatizace na poplachové události

Každá změna poplachového příznaku vystřelí událost `ja_rs485_alarm` s daty
`{"type": "intruder"|"fire"|"panic", "flag": "...", "section": N, "active": true|false}`:

```yaml
trigger:
  - platform: event
    event_type: ja_rs485_alarm
    event_data:
      active: true
action:
  - service: notify.mobile_app_phone
    data:
      title: "ALARM!"
      message: "Poplach {{ trigger.event.data.type }} v sekci {{ trigger.event.data.section }}"
```

## Ověřený hardware

Ověřeno na systému JABLOTRON 100+ s JA-121T a USB↔RS-485 převodníkem na čipu FT232R
(`/dev/ttyUSB0`), zapojení A→D+, B→D−, GND↔GND, s externím 12 V DC zdrojem na svorkách
+U/GND výstupní strany modulu. Zapnutí/vypnutí sekcí, ovládání PG i čtení čidel potvrzeno
na reálném hardwaru. Praktické poznatky: změny PG výstupů se propisují okamžitě, aktualizace
čidel (PRFSTATE) chodí jen cca každých 10 s — pro automatizace veď čidla přes PG výstupy.

## Řešení problémů

| Příznak | Co zkontrolovat |
|---------|-----------------|
| `invalid_auth` / `NO_ACCESS` v logu | Špatný kód, špatný prefix, nebo kód nemá práva na danou sekci/PG |
| `no_response` při nastavení | Prohozené vodiče A/B, chybějící GND, špatný port, nebo JA-121T není v režimu Terminál |
| `unexpected_data` / ojedinělé rozbité bajty (`\x00`, `\xfc`) v logu | **Chybí 12 V napájení RS-485 strany (+U/GND)** nebo obrácená polarita A/B |
| Entity existují, ale nikdy se neaktualizují | V F-Linku je zapnutý *Pasivní režim* — vypni ho, ať modul změny sám posílá |
| Všechno spadne do `unavailable` | Odpojený USB převodník; integrace se připojí sama znovu |

## Licence

MIT
