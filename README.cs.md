<p align="center"><img src="brands/logo@2x.png" alt="JA-RS485" width="461"></p>

# JA-RS485 â€” Jablotron v Home Assistantu pĹ™es sbÄ›rnicovĂ© rozhranĂ­ JA-121T (RS-485)

[English](README.md) | **ÄŚeĹˇtina**

[![Validate](https://github.com/vlioscz/JA-RS485/actions/workflows/validate.yml/badge.svg)](https://github.com/vlioscz/JA-RS485/actions/workflows/validate.yml)
[![GitHub release](https://img.shields.io/github/v/release/vlioscz/JA-RS485)](https://github.com/vlioscz/JA-RS485/releases)
[![HACS](https://img.shields.io/badge/HACS-Default-blue.svg)](https://hacs.xyz)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Custom integrace pro Home Assistant â€” ÄŤtenĂ­ a ovlĂˇdĂˇnĂ­ zabezpeÄŤovacĂ­ho systĂ©mu
**Jablotron JABLOTRON 100 / 100+** pĹ™es **[sbÄ›rnicovĂ© rozhranĂ­ JA-121T (RS-485)](https://portal.jablotron.com/cs/sbernicove-rozhrani-rs-485)**
(ASCII protokol, 9600 Bd, 8N1 â€” dle Jablotron manuĂˇlu MNN51111), typicky pĹ™ipojenĂ© USBâ†”RS-485 pĹ™evodnĂ­kem.

## ProÄŤ zrovna RS-485? (srovnĂˇnĂ­ s ostatnĂ­mi Jablotron integracemi)

Do Home Assistantu jde Jablotron dostat i jinak:

- **[Jablotron Cloud](https://github.com/Pigotka/ha-cc-jablotron-cloud)** â€” pouĹľĂ­vĂˇ cloudovĂ© API
  MyJABLOTRON. Ĺ˝ĂˇdnĂˇ kabelĂˇĹľ, ale zĂˇvisĂ­ na tvĂ©m internetovĂ©m pĹ™ipojenĂ­ *a* na dostupnosti
  Jablotron cloudu: kdyĹľ vypadne kterĂ©koliv z toho, vypadne i alarm v HA.
- **[Jablotron 100](https://github.com/kukulich/home-assistant-jablotron100)** â€” pĹ™ipojuje se
  pĹ™Ă­mo do ĂşstĹ™edny pĹ™es USB. UmĂ­ toho hodnÄ›, ale HA musĂ­ stĂˇt hned vedle ĂşstĹ™edny, USB kabel
  mĹŻĹľe nÄ›kdo omylem vytĂˇhnout a na vÄ›tĹˇĂ­ vzdĂˇlenost musĂ­Ĺˇ Ĺ™eĹˇit, jak USB prodlouĹľit (na coĹľ
  nebylo nikdy stavÄ›nĂ©).

Tato integrace moĹľnĂˇ nenabĂ­zĂ­ ĂşplnÄ› vĹˇechny funkce tÄ›ch dvou, zato je **nejhĹŻĹ™ rozbitnĂˇ**:
JA-121T komunikuje po vyhrazenĂ© sbÄ›rnici RS-485 â€” prĹŻmyslovĂ©m standardu navrĹľenĂ©m na stovky
metrĹŻ obyÄŤejnĂ© kroucenĂ© dvojlinky, s galvanickĂ˝m oddÄ›lenĂ­m a ĹˇroubovacĂ­mi svorkami, kterĂ©
nevypadnou. VĹˇechno bÄ›ĹľĂ­ **ÄŤistÄ› lokĂˇlnÄ›** (ĹľĂˇdnĂ˝ internet, ĹľĂˇdnĂ˝ cloudovĂ˝ ĂşÄŤet), a kdyby
linka pĹ™ece jen spadla, integrace se sama znovu pĹ™ipojĂ­ a dĂˇ ti o tom vÄ›dÄ›t
(`binary_sensor.jablotron_bus_connection`).

## Funkce

- **Alarm panel** (entita `alarm_control_panel`) pro kaĹľdou sekci â€” zapnutĂ­ (SET), ÄŤĂˇsteÄŤnĂ©
  zapnutĂ­ (SETP), vypnutĂ­ (UNSET), se sprĂˇvnĂ˝mi stavy HA: `disarmed`, `arming` (odchodovĂ©
  zpoĹľdÄ›nĂ­), `pending` (pĹ™Ă­chodovĂ© zpoĹľdÄ›nĂ­), `armed_away`, `armed_home` a `triggered`
  (poplach vloupĂˇnĂ­ / poĹľĂˇr / tĂ­seĹ)
- **Switch** pro kaĹľdĂ˝ PG vĂ˝stup (PGON / PGOFF), bez optimismu â€” stav se pĹ™epne aĹľ potĂ©,
  co ho ĂşstĹ™edna potvrdĂ­. PG nakonfigurovanĂ© v F-Linku jako **impuls** staÄŤĂ­ uvĂ©st
  v nastavenĂ­ a vytvoĹ™Ă­ se mĂ­sto pĹ™epĂ­naÄŤe jako **tlaÄŤĂ­tko** (stisk = PGON)
- **Device triggery** â€” â€žPoplach vloupĂˇnĂ­ / PoĹľĂˇrnĂ­ / TĂ­sĹovĂ˝ / JakĂ˝koliv" (volitelnÄ› pro
  jednu sekci) vybereĹˇ pĹ™Ă­mo v UI editoru automatizacĂ­
- **DiagnostickĂ˝ sensor** pro kaĹľdou sekci se surovĂ˝m stavem JA-121T (`READY`, `ARMED`,
  `ARMED_PART`, `BLOCKED`, `SERVICE`, â€¦) a aktivnĂ­mi pĹ™Ă­znaky v atributech
- **Binary sensor** pro kaĹľdou periferii (ÄŤidlo) dekĂłdovanĂ˝ z bitmapy `PRFSTATE` â€” vytvoĹ™Ă­ se
  automaticky pĹ™i prvnĂ­ aktivaci, nebo vyber pozice explicitnÄ› v nastavenĂ­ integrace (ÄŤĂ­sla
  odpovĂ­dajĂ­ zĂˇloĹľce ZaĹ™Ă­zenĂ­ v F-Linku, 0 = ĂşstĹ™edna). Pozn.: protokol nenese nĂˇzvy ani typy
  ÄŤidel â€” entity si pĹ™ejmenuj v HA
- **Import z F-Linku** â€” protokol JA-121T nĂˇzvy nenese, ale F-Link umĂ­ exportovat strĂˇnky
  Sekce / PG vĂ˝stupy / ZaĹ™Ă­zenĂ­ do CSV/TXT. Nahraj tyto exporty v nastavenĂ­ integrace
  (â€žImport nĂˇzvĹŻ z F-Linku") a entity dostanou skuteÄŤnĂ© nĂˇzvy; z PG exportu se navĂ­c
  automaticky nastavĂ­ seznam impulsnĂ­ch PG (tlaÄŤĂ­tek) a skryjĂ­ nepouĹľĂ­vanĂ© vĂ˝stupy.
  ÄŚistÄ› lokĂˇlnĂ­, ĹľĂˇdnĂ˝ cloud
- **Filtr entit** v nastavenĂ­ integrace â€” vyber, kterĂ© sekce, PG vĂ˝stupy a periferie se majĂ­
  vytvĂˇĹ™et jako entity (stavovĂ© dotazy nejsou omezenĂ© prĂˇvy kĂłdu, takĹľe standardnÄ› je vidÄ›t
  vĹˇe, co ĂşstĹ™edna hlĂˇsĂ­)
- **PrĂˇva ovlĂˇdĂˇnĂ­** v nastavenĂ­ integrace, zrcadlĂ­cĂ­ prĂˇva pĹ™Ă­stupovĂ©ho kĂłdu z F-Linku:
  typ ovlĂˇdĂˇnĂ­ sekcĂ­ (plnĂ˝ / jen zakĂłdovat / jen ÄŤtenĂ­), kterĂ© sekce lze ovlĂˇdat a zda/kterĂ©
  PG vĂ˝stupy lze ovlĂˇdat. ZakĂˇzanĂ© povely se odmĂ­tnou lokĂˇlnÄ› se srozumitelnou chybou, mĂ­sto
  aby se zkouĹˇely proti ĂşstĹ™ednÄ› (`NO_ACCESS` pokusy by zaplevelily historii udĂˇlostĂ­
  Jablotronu)
- Sekce a PG vĂ˝stupy se **objevujĂ­ automaticky** ze sbÄ›rnice (poÄŤĂˇteÄŤnĂ­ dotaz
  `STATE` / `PGSTATE` + spontĂˇnnĂ­ hlĂˇĹˇenĂ­); novĂ© se pĹ™idajĂ­ bez restartu
- **Push aktualizace** â€” zmÄ›ny sekcĂ­ a PG hlĂˇsĂ­ JA-121T okamĹľitÄ›. Stavy ÄŤidel (PRFSTATE)
  ĂşstĹ™edna vysĂ­lĂˇ jen cca kaĹľdĂ˝ch 10 s, takĹľe binary sensory ÄŤidel jsou **pouze
  informativnĂ­** â€” pro automatizace veÄŹ ÄŤidlo v F-Linku pĹ™es PG vĂ˝stup (zmÄ›ny PG chodĂ­
  okamĹľitÄ›). KaĹľdĂ˝ch 5 minut bÄ›ĹľĂ­ plnĂˇ resynchronizace stavĹŻ, kterĂˇ doĹľene cokoliv
  ztracenĂ©ho kolizemi na poloduplexnĂ­ lince
- **AutomatickĂ˝ reconnect** s backoffem, kdyĹľ sĂ©riovĂ˝ port zmizĂ­ (napĹ™. pĹ™epojenĂ­ USB);
  entity jsou mezitĂ­m `unavailable`
- Config flow ovÄ›Ĺ™Ă­ spojenĂ­ i pĹ™Ă­stupovĂ˝ kĂłd jeĹˇtÄ› pĹ™ed vytvoĹ™enĂ­m zĂˇznamu;
  **Znovu nakonfigurovat** umoĹľnĂ­ pozdÄ›ji zmÄ›nit port nebo kĂłd bez ztrĂˇty entit
- UdĂˇlost **`ja_rs485_alarm`** na sbÄ›rnici HA pĹ™i kaĹľdĂ© zmÄ›nÄ› poplachovĂ©ho pĹ™Ă­znaku sekce â€”
  ideĂˇlnĂ­ pro push notifikace
- **Binary sensor stavu spojenĂ­** (`binary_sensor.jablotron_bus_connection`) pro hlĂ­dĂˇnĂ­
  sĂ©riovĂ© linky
- **Diagnostika** ke staĹľenĂ­ (pĹ™Ă­stupovĂ˝ kĂłd zaÄŤernÄ›nĂ˝) vÄŤetnÄ› poslednĂ­ch 50 pĹ™ijatĂ˝ch Ĺ™ĂˇdkĹŻ
  protokolu â€” pĹ™iloĹľ ji, kdyĹľ hlĂˇsĂ­Ĺˇ problĂ©m
- Entity sekcĂ­ majĂ­ atribut `state_changed_at` (UTC) s ÄŤasem poslednĂ­ hlĂˇĹˇenĂ© zmÄ›ny stavu

## BezpeÄŤnostnĂ­ poznĂˇmky

- VeĹˇkerĂˇ komunikace bÄ›ĹľĂ­ ve vyhrazenĂ©m vlĂˇknÄ› â€” nic neblokuje event loop HA.
- Povely se sklĂˇdajĂ­ vĂ˝hradnÄ› z validovanĂ˝ch ÄŤĂ­sel (sekce 1â€“15, PG 1â€“128); pĹ™Ă­stupovĂ˝ kĂłd mĂˇ
  omezenou znakovou sadu uĹľ pĹ™i nastavenĂ­. Nic od uĹľivatele nemĹŻĹľe na linku propaĹˇovat dalĹˇĂ­
  pĹ™Ă­kazy.
- PĹ™Ă­stupovĂ˝ kĂłd je uloĹľenĂ˝ v config entry HA a **nikdy se nezapisuje do logĹŻ**.
- **VyhraÄŹ integraci samostatnĂ˝ uĹľivatelskĂ˝ kĂłd** jen s potĹ™ebnĂ˝mi prĂˇvy (kterĂ© sekce smĂ­
  ovlĂˇdat, kterĂ© PG vĂ˝stupy). KaĹľdĂ˝ povel se zapisuje do historie udĂˇlostĂ­ Jablotronu pod
  tĂ­mto uĹľivatelem.
- NeĂşspÄ›ĹˇnĂ© povely (napĹ™. `ERROR: 3 NO_ACCESS`) se logujĂ­ a u zapnutĂ­/vypnutĂ­ se chyba ukĂˇĹľe
  pĹ™Ă­mo v UI â€” nikdy se nepĹ™edstĂ­rĂˇ ĂşspÄ›ch.

## PoĹľadavky

- Home Assistant 2024.11 nebo novÄ›jĹˇĂ­
- JA-121T nauÄŤenĂ˝ v ĂşstĹ™ednÄ›, reĹľim **TerminĂˇl** (vĂ˝chozĂ­; nastavuje se v F-Linku â†’
  VnitĹ™nĂ­ nastavenĂ­)
- USBâ†”RS-485 pĹ™evodnĂ­k (FTDI / CH340 / CP2102 â€” fungujĂ­ vĹˇechny)

### ZapojenĂ­ (dvÄ› vÄ›ci, kterĂ© kaĹľdĂ˝ zkazĂ­)

1. **ExternĂ­ napĂˇjenĂ­ 12 V je povinnĂ©.** RS-485 strana JA-121T je galvanicky oddÄ›lenĂˇ
   a **nenapĂˇjĂ­ se** ze sbÄ›rnice Jablotronu. PĹ™iveÄŹ **12 V DC** (dle manuĂˇlu 6â€“28 V) na
   svorky **+U/GND na vĂ˝stupnĂ­ (RS-485) stranÄ›**. Bez nÄ›j je na lince jen Ĺˇum (ojedinÄ›lĂ©
   rozbitĂ© bajty typu `\x00`).
2. **Polarita datovĂ˝ch vodiÄŤĹŻ:** JA-121T **A â†’ D+ pĹ™evodnĂ­ku**, **B â†’ Dâ’**, a propoj **GND**
   vĂ˝stupnĂ­ strany JA-121T se zemĂ­ pĹ™evodnĂ­ku. (ZnaÄŤenĂ­ A/B u RS-485 nenĂ­ standardizovanĂ© â€”
   pokud s pĹ™ipojenĂ˝m napĂˇjenĂ­m chodĂ­ jen smetĂ­, prohoÄŹ A/B.)

## Instalace

### HACS (doporuÄŤeno)

[![OtevĹ™e tvou instanci Home Assistanta a zobrazĂ­ tento repozitĂˇĹ™ v HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=vlioscz&repository=JA-RS485&category=integration)

Integrace je ve vĂ˝chozĂ­m HACS store: klikni na tlaÄŤĂ­tko vĂ˝Ĺˇe, nebo vyhledej
**JA-RS485** pĹ™Ă­mo v HACS, stĂˇhni a restartuj Home Assistant.

### RuÄŤnÄ›

1. ZkopĂ­ruj `custom_components/ja_rs485/` do `config/custom_components/ja_rs485/`.
2. Restartuj Home Assistant.

### NastavenĂ­

[![OtevĹ™e tvou instanci Home Assistanta a spustĂ­ nastavenĂ­ tĂ©to integrace.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=ja_rs485)

1. Klikni na tlaÄŤĂ­tko vĂ˝Ĺˇe, nebo **NastavenĂ­ â†’ ZaĹ™Ă­zenĂ­ a sluĹľby â†’ PĹ™idat integraci â†’ JA-RS485.**
2. Vyber sĂ©riovĂ˝ port â€” radĹˇi stabilnĂ­ cestu `/dev/serial/by-id/usb-...` neĹľ `/dev/ttyUSB0`
   (pĹ™eĹľije restarty a pĹ™epojenĂ­) â€” a zadej pĹ™Ă­stupovĂ˝ kĂłd (s prefixem, pokud jej systĂ©m
   pouĹľĂ­vĂˇ, napĹ™. `1*1234`).

## SluĹľby

ZachovanĂ© pro zpÄ›tnou kompatibilitu a automatizace; preferovanĂˇ cesta jsou entity
alarmu/switche.

| SluĹľba | Povel | Popis |
|--------|-------|-------|
| `ja_rs485.set_zone` | `SET n` | Zapne sekci (1â€“15) |
| `ja_rs485.set_zone_partial` | `SETP n` | ÄŚĂˇsteÄŤnÄ› zapne sekci |
| `ja_rs485.unset_zone` | `UNSET n` | Vypne sekci |
| `ja_rs485.pgon` | `PGON n` | Zapne PG vĂ˝stup (1â€“128) |
| `ja_rs485.pgoff` | `PGOFF n` | Vypne PG vĂ˝stup |

## Lovelace dashboard

`dashboards/jablotron_dashboard.yaml` automaticky vygeneruje dlaĹľdice pro vĹˇechny sekce
(s tlaÄŤĂ­tky zapnout/vypnout) a PG vĂ˝stupy. PotĹ™ebuje jen plugin
[auto-entities](https://github.com/thomasloven/lovelace-auto-entities) (HACS).

## Automatizace na poplachovĂ© udĂˇlosti

KaĹľdĂˇ zmÄ›na poplachovĂ©ho pĹ™Ă­znaku vystĹ™elĂ­ udĂˇlost `ja_rs485_alarm` s daty
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

## OvÄ›Ĺ™enĂ˝ hardware

OvÄ›Ĺ™eno na systĂ©mu JABLOTRON 100+ s JA-121T a USBâ†”RS-485 pĹ™evodnĂ­kem na ÄŤipu FT232R
(`/dev/ttyUSB0`), zapojenĂ­ Aâ†’D+, Bâ†’Dâ’, GNDâ†”GND, s externĂ­m 12 V DC zdrojem na svorkĂˇch
+U/GND vĂ˝stupnĂ­ strany modulu. ZapnutĂ­/vypnutĂ­ sekcĂ­, ovlĂˇdĂˇnĂ­ PG i ÄŤtenĂ­ ÄŤidel potvrzeno
na reĂˇlnĂ©m hardwaru. PraktickĂ© poznatky: zmÄ›ny PG vĂ˝stupĹŻ se propisujĂ­ okamĹľitÄ›, aktualizace
ÄŤidel (PRFSTATE) chodĂ­ jen cca kaĹľdĂ˝ch 10 s â€” pro automatizace veÄŹ ÄŤidla pĹ™es PG vĂ˝stupy.

## ĹeĹˇenĂ­ problĂ©mĹŻ

| PĹ™Ă­znak | Co zkontrolovat |
|---------|-----------------|
| `invalid_auth` / `NO_ACCESS` v logu | Ĺ patnĂ˝ kĂłd, ĹˇpatnĂ˝ prefix, nebo kĂłd nemĂˇ prĂˇva na danou sekci/PG |
| `no_response` pĹ™i nastavenĂ­ | ProhozenĂ© vodiÄŤe A/B, chybÄ›jĂ­cĂ­ GND, ĹˇpatnĂ˝ port, nebo JA-121T nenĂ­ v reĹľimu TerminĂˇl |
| `unexpected_data` / ojedinÄ›lĂ© rozbitĂ© bajty (`\x00`, `\xfc`) v logu | **ChybĂ­ 12 V napĂˇjenĂ­ RS-485 strany (+U/GND)** nebo obrĂˇcenĂˇ polarita A/B |
| Entity existujĂ­, ale nikdy se neaktualizujĂ­ | V F-Linku je zapnutĂ˝ *PasivnĂ­ reĹľim* â€” vypni ho, aĹĄ modul zmÄ›ny sĂˇm posĂ­lĂˇ |
| VĹˇechno spadne do `unavailable` | OdpojenĂ˝ USB pĹ™evodnĂ­k; integrace se pĹ™ipojĂ­ sama znovu |

## Licence

MIT
