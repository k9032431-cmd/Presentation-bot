# Shiri-Presentation-BOT 🎨

Telegram boty: temany ýazýarsyňyz, bot size owadan **PowerPoint (.pptx)** prezentasiýa taýýarlap berýär.

## Mümkinçilikler

| Görnüş | Slaýd | Näme bar |
|---|---|---|
| 🟢 **Ýönekeý** | 6 | Arassa dizaýn, sözbaşy + punktlar |
| 🟡 **Orta** | 10 | Mazmuny, suratlar, kartoçkalar, statistika, deňeşdirme, sitata, geçişler |
| 🔴 **Doly (Full)** | 14 | Ortadakylaryň hemmesi + diagramma, tapgyrlar, timeline, doly ekran surat, **elementleriň animasiýasy**, dürli slaýd geçişleri, spiker bellikleri |

* Ulanyjy **slaýd sanyny** düwmeden saýlaýar ýa-da özi ýazýar (3–30).
* **Rugsat ulgamy**: boty diňe admin rugsat beren adamlar ulanyp bilýär. Täze adam `/start` basanda admine «✅ Rugsat ber / ⛔ Ret et» düwmeli habar gelýär. Admin panelde: «⏳ Rugsat garaşýanlar», «👥 Rugsatly ulanyjylar» (rugsady aýyrmak), ýa-da kommanda bilen: `/allow 123456789`, `/deny 123456789`.
* Görnüş saýlanandan soň bot **stilleriň suratlaryny** görkezýär (◀️ ▶️), ulanyjy halanyny saýlaýar.
* 8 sany taýýar stil bar (Corporate Blue, Emerald Business, Dark Luxury, Ocean Teal, Sunset Pitch, Minimal Gray, Royal Purple, Navy Gold).
* **Suratdan stil (awtomatik):** admin bota islendik prezentasiýa dizaýnynyň suratyny (Pinterest, skrinşot) iberýär — bot AI bilen reňkleri, bezegi we şrifti özi saýlap, görkeziş suratyny çykarýar. AI işlemese, reňkler suratdan hasaplanýar.
* **Admin** bot arkaly el bilen hem täze stil goşup bilýär: `⚙️ Admin panel → ➕ Täze stil goş` (ady → 5 reňk → bezeg → şrift → görkeziş → ýatda sakla).
* Admin panelde: stilleri pozmak, statistika, ähli ulanyjylara habar ibermek.
* Diller: Türkmençe, Русский, English.

## Serwere gurnamak (1 kommanda)

Ubuntu 22.04+ / Debian 12+ serwerde:

```bash
curl -fsSL https://raw.githubusercontent.com/k9032431-cmd/Presentation-bot/claude/amazing-dirac-9qiwys/install.sh | sudo bash
```

Skript özi soraýar:
1. **BOT_TOKEN** — [@BotFather](https://t.me/BotFather)-de `/newbot` bilen alynýar
2. **ADMIN_IDS** — öz Telegram ID-ňiz ([@userinfobot](https://t.me/userinfobot))
3. **ANTHROPIC_API_KEY** — [console.anthropic.com](https://console.anthropic.com) (prezentasiýanyň tekstini ýazýan AI)
4. **PEXELS_API_KEY** — islege görä, mugt: [pexels.com/api](https://www.pexels.com/api) (slaýdlara hakyky suratlar). Bolmasa, suratlaryň ýerine owadan geometrik bezegler goýulýar.

Bot `systemd` hyzmaty hökmünde işleýär: serwer öçüp-ýansa hem özi açylýar.

### Dolandyrmak

```bash
systemctl status shiri-presentation-bot
```

```bash
journalctl -u shiri-presentation-bot -f
```

```bash
sudo bash /opt/shiri-presentation-bot/install.sh
```

(soňky kommanda: kody täzeläp boty täzeden başladýar)

Sazlamalary üýtgetmek: `nano /opt/shiri-presentation-bot/.env`, soňra `systemctl restart shiri-presentation-bot`.

## Gurluşy

```
bot/
  main.py            – başlangyç nokat
  config.py          – .env sazlamalary
  ai.py              – Claude bilen mazmun döretmek (her derejäniň slaýd meýilnamasy)
  builder/deck.py    – slaýd dizaýnlary (15 görnüş)
  builder/anim.py    – geçişler we animasiýalar
  preview.py         – stil görkeziş suratlary
  default_styles.py  – başlangyç stiller
  handlers/user.py   – ulanyjy menýusy
  handlers/admin.py  – admin panel
install.sh           – serwere gurnamak
```
