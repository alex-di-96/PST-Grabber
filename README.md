# PST-Grabber 🚀  `[v 0.12]`

[RU] Ультимативный конвертер Outlook **PST → Thunderbird (MBOX)**. Один файл, без облаков, без регистраций, без «купите PRO-версию за $49».
[EN] The ultimate Outlook **PST → Thunderbird (MBOX)** converter. Single file, no cloud, no sign-ups, no "buy PRO for $49".

> [RU] Сделано за один вечер, чтобы не платить за проприетарные конвертеры. Если сэкономило минуту вашей жизни — поставьте ⭐.
> [EN] Built in one evening to avoid paying for proprietary converters. If it saved you a minute — drop a ⭐.

---

## Содержание / Table of Contents
- [Зачем это нужно / Why](#зачем-это-нужно--why)
- [Особенности / Features](#особенности--features)
- [Как это работает / How it works](#как-это-работает--how-it-works)
- [Требования / Requirements](#требования--requirements)
- [Установка / Setup](#установка--setup)
- [Запуск / Running](#запуск--running)
- [GUI](#использование--usage-gui)
- [CLI](#использование--usage-cli)
- [Структура результата / Output & Thunderbird import](#структура-результата--output--thunderbird-import)
- [Решение проблем / Troubleshooting](#решение-проблем--troubleshooting)
- [Сборка / Build](#сборка--build)

---

## Зачем это нужно / Why

[RU] Outlook хранит почту в `.pst`, Thunderbird — в формате **MBOX** с `.sbd`-структурой для вложенных папок. Прямого импорта между ними нет, а онлайн-конвертеры либо платные, либо хотят залить вашу корпоративную переписку к себе на сервер. PST-Grabber делает всё локально.

[EN] Outlook stores mail in `.pst`, Thunderbird uses **MBOX** with an `.sbd` tree for nested folders. There is no direct import, and online converters are either paid or want to upload your corporate mail to their servers. PST-Grabber does everything locally.

---

## Особенности / Features

* **Hybrid Engine / Гибридный движок**
    * [RU] Использует высокопроизводительный `readpst` (C) или встроенный Python-движок как fallback.
    * [EN] Uses high-performance `readpst` (C) with a built-in Python engine as a fallback.
    * ⚠️ **WARNING:** [RU] Встроенный Python-движок (`libpff`) — это аварийный вариант: из повреждённых PST он вытаскивает примерно в 10 раз меньше писем, чем `readpst`. На Windows настоятельно рекомендуется скачать бинарь (кнопка **Download Engine** прямо в интерфейсе).
    * [EN] The built-in Python engine (`libpff`) is a last resort: it extracts roughly 10× fewer emails from corrupted PSTs than `readpst`. On Windows, grab the binary via the in-app **Download Engine** button.
* **Auto-download Engine / Авто-загрузка движка**
    * [RU] Кнопка **Download Engine** сама качает `readpst.exe` + DLL и складывает их в локальную папку `rpst/` (без мусора в корне проекта).
    * [EN] The **Download Engine** button fetches `readpst.exe` + DLLs into a local `rpst/` folder (no clutter in the project root).
* **Thunderbird Ready**
    * [RU] Автоматически создаёт структуру `.sbd` для вложенных папок.
    * [EN] Automatically builds the `.sbd` structure for nested folders.
* **Кириллица / Cyrillic safe** — [RU] принудительный UTF-8 (`-u`), никаких «кракозябр». / [EN] forced UTF-8 (`-u`), no mojibake.
* **Data Recovery** — [RU] режим `-k` для восстановления повреждённых PST. / [EN] `-k` mode for recovering corrupted PSTs.
* **TNEF Extraction** — [RU] распаковка вложений из `winmail.dat`. / [EN] extracts attachments from `winmail.dat`.
* **GUI + headless CLI** — [RU] графика на `customtkinter` и полностью консольный режим для серверов/автоматизации. / [EN] `customtkinter` GUI plus a fully headless CLI for servers/automation.

---

## Как это работает / How it works

[RU] Программа выбирает движок в таком порядке:
[EN] The engine is selected in this order:

1. `rpst/readpst.exe` (или `readpst`) — [RU] локально скачанный движок рядом с программой. / [EN] locally downloaded engine next to the app.
2. `readpst` из системного `PATH` (Linux: `pst-utils`).
3. `pypff` (libpff) — [RU] Python-fallback. / [EN] Python fallback.

[RU] Для `readpst` вызывается `readpst -u -M -r -o <temp>` (+`-k` при recovery), после чего результат раскладывается в Thunderbird-иерархию `Папка` + `Папка.sbd/`, а вложения из `winmail.dat` распаковываются через `tnef`.
[EN] For `readpst` it runs `readpst -u -M -r -o <temp>` (+`-k` for recovery), then reorganizes the output into the Thunderbird `Folder` + `Folder.sbd/` layout and unpacks `winmail.dat` attachments via `tnef`.

---

## Требования / Requirements

* Python **3.10+**
* [RU] Зависимости из `requirements.txt` (`customtkinter`, `tnefparse`, `libpff-python`, …).
* [EN] Dependencies from `requirements.txt` (`customtkinter`, `tnefparse`, `libpff-python`, …).
* [RU] **Опционально, но рекомендуется:** `readpst` (Windows — кнопкой в GUI, Linux — `pst-utils`).
* [EN] **Optional but recommended:** `readpst` (Windows — via the GUI button, Linux — `pst-utils`).

---

## Установка / Setup

### Windows

```powershell
python -m venv venv
.\venv\Scripts\python -m pip install -r requirements.txt
```

[RU] Движок `readpst` качается прямо из интерфейса кнопкой **"Download Engine"** — он попадёт в папку `rpst/`.
[EN] The `readpst` engine is fetched from the UI via the **"Download Engine"** button — it lands in the `rpst/` folder.

*(Manual download if needed: [libpst-0.6.63-w32-bin.zip](https://sourceforge.net/projects/ezwinports/files/libpst-0.6.63-w32-bin.zip/download) → распакуйте `bin/*.exe` и `bin/*.dll` в папку `rpst/`)*

### Linux

```bash
sudo apt update && sudo apt install pst-utils tnef python3-tk
python3 -m venv venv
venv/bin/python -m pip install -r requirements.txt
```

---

## Запуск / Running

[RU] Активировать venv **не нужно** — достаточно вызвать интерпретатор из venv напрямую:
[EN] You **don't** need to activate the venv — just call the venv's interpreter directly:

```powershell
# Windows
.\venv\Scripts\python pst_grabber.py
```

```bash
# Linux
venv/bin/python pst_grabber.py
```

[RU] Если зависимости стоят глобально, можно просто:
[EN] If dependencies are installed globally, simply:

```bash
python pst_grabber.py        # Windows
python3 pst_grabber.py       # Linux
```

---

## Использование / Usage (GUI)

1. [RU] Выберите PST-файл или папку. / [EN] Pick a PST file or folder.
2. [RU] Укажите папку назначения. / [EN] Choose the output folder.
3. [RU] (Опц.) включите **Recover Mode (-k)** и **Extract TNEF**. / [EN] (Opt.) toggle **Recover Mode (-k)** and **Extract TNEF**.
4. [RU] Нажмите **START CONVERSION**. / [EN] Click **START CONVERSION**.
5. [RU] Скопируйте результат в / [EN] Copy the result into:
   `~/.thunderbird/<profile>/Mail/Local Folders/`

---

## Использование / Usage (CLI)

[RU] **Важно:** для headless-режима обязателен флаг `--cli`. Без него `-s/-d` лишь предзаполнят поля GUI.
[EN] **Important:** the headless mode requires the `--cli` flag. Without it, `-s/-d` only pre-fill the GUI fields.

### Python

```bash
# Базовая конвертация / Basic conversion
python pst_grabber.py --cli -s /path/to/source.pst -d /path/to/output

# Папка целиком (рекурсивно ищет все .pst) / Whole folder (recursive .pst scan)
python pst_grabber.py --cli -s /path/to/pst_folder -d /path/to/output

# Отключить recovery и TNEF / Disable recovery and TNEF
python pst_grabber.py --cli -s input.pst -d output --no-recover --no-tnef
```

### Скомпилированный бинарь / Compiled binary

```powershell
:: Windows
PST-Grabber.exe --cli -s "C:\Mail\archive.pst" -d "C:\ExportedMail"
```

```bash
# Linux
./PST-Grabber --cli -s /home/user/mail.pst -d /home/user/export
```

| Флаг / Flag | [RU] Описание / [EN] Description |
|---|---|
| `-s, --source` | [RU] PST-файл или папка с PST. / [EN] PST file or folder of PSTs. |
| `-d, --dest`   | [RU] Папка назначения для MBOX. / [EN] Output folder for MBOX. |
| `--cli`        | [RU] Headless-режим без GUI. / [EN] Headless mode, no GUI. |
| `--no-recover` | [RU] Отключить режим восстановления `-k`. / [EN] Disable recovery mode `-k`. |
| `--no-tnef`    | [RU] Отключить распаковку `winmail.dat`. / [EN] Disable `winmail.dat` extraction. |

---

## Структура результата / Output & Thunderbird import

[RU] На выходе для каждого PST создаётся файл-папка и её `.sbd`-дерево, например:
[EN] For each PST you get a mailbox file plus its `.sbd` tree, e.g.:

```
output/
├── mailbox                 # файл MBOX верхнего уровня / top-level MBOX file
└── mailbox.sbd/
    ├── Inbox
    ├── Inbox.sbd/
    │   ├── Project
    │   └── Project.sbd/
    └── Sent
```

[RU] Скопируйте содержимое в `~/.thunderbird/<profile>/Mail/Local Folders/` при закрытом Thunderbird — папки появятся в «Локальных папках».
[EN] Copy the contents into `~/.thunderbird/<profile>/Mail/Local Folders/` with Thunderbird closed — the folders will show up under "Local Folders".

---

## Решение проблем / Troubleshooting

* **«Кракозябры» / Mojibake** — [RU] старые ANSI-PST: `readpst -u` уже включён; если осталось — в Thunderbird ПКМ по папке → Свойства → Кодировка → Cyrillic (Windows-1251). / [EN] legacy ANSI PSTs: `-u` is already on; otherwise set the folder encoding to Cyrillic (Windows-1251) in Thunderbird.
* **`winmail.dat`** — [RU] включите **Extract TNEF** или поставьте плагин **LookOut (fix)**. / [EN] enable **Extract TNEF** or install the **LookOut (fix)** add-on.
* **Огромные файлы / Huge files (50 GB+)** — [RU] используйте `readpst` (потоковый, мало RAM), а не Python-fallback. / [EN] use `readpst` (streaming, low RAM), not the Python fallback.
* **Download Engine не работает / fails** — [RU] зеркало SourceForge могло лечь: скачайте zip вручную и распакуйте в `rpst/`. / [EN] the SourceForge mirror may be down: download the zip manually and unzip into `rpst/`.

[RU] Подробный разбор подводных камней — в [`Research/findings.md`](Research/findings.md).
[EN] A detailed write-up of the pitfalls lives in [`Research/findings.md`](Research/findings.md).

---

## Сборка / Build

```bash
# Windows / Linux
pyinstaller --noconfirm --onefile --windowed --name "PST-Grabber" pst_grabber.py
```

---

**Powered by [aLex Di](https://github.com/alex-di-96/)** · `v 0.12`
