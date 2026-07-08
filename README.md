# extractors — сервис извлечения текстового слоя

Модульный сервис для извлечения **текстового слоя** из документов произвольного
формата. Принимает файл (по пути или в виде байтов), определяет его тип, выбирает
подходящий экстрактор и возвращает извлечённый текст. Если текстового слоя в
документе нет (скан, фотография, изображение) — файл автоматически направляется
в **OCR** (сейчас подключена заглушка, готовая к замене на реальный движок).

---

## Содержание

- [Возможности](#возможности)
- [Поддерживаемые форматы](#поддерживаемые-форматы)
- [Архитектура](#архитектура)
- [Конвейер обработки](#конвейер-обработки)
- [Проверка текстового слоя и OCR](#проверка-текстового-слоя-и-ocr)
- [Установка](#установка)
- [Использование](#использование)
- [CLI](#cli)
- [Markdown-режим (`--md` / `markdown=True`)](#markdown-режим---md--markdowntrue)
- [Модель результата](#модель-результата)
- [Коды ошибок и статусы](#коды-ошибок-и-статусы)
- [Как добавить новый формат](#как-добавить-новый-формат)
- [Структура проекта](#структура-проекта)
- [Заметки по миграции](#заметки-по-миграции)

---

## Возможности

- **Единый вход** для всех форматов: путь к файлу или байты.
- **Автоопределение MIME** по содержимому (libmagic) и по расширению, с особой
  обработкой OOXML-контейнеров (docx/xlsx/pptx, которые libmagic путает с zip).
- **Автоопределение кодировки** текстовых файлов (UTF-8 → charset-normalizer →
  latin-1), корректная обработка BOM.
- **Проверка наличия текстового слоя** и **маршрутизация в OCR** для сканов и
  изображений.
- **Markdown-режим** (`--md` / `markdown=True`): читает документ в Markdown с
  сохранением таблиц (markitdown + нативные md-рендеры) — для подачи в LLM.
- **Рекурсивная обработка архивов** — текст извлекается из вложенных файлов тем
  же конвейером.
- **Мягкая деградация**: тяжёлые/редкие библиотеки импортируются лениво; если
  зависимость не установлена, пакет продолжает работать, а формат возвращает
  понятный код `DEPENDENCY_MISSING` (YAML без PyYAML отдаётся как сырой текст).
- **Автономность**: пакет не зависит от внешних модулей проекта, встроен лёгкий
  логгер с интерфейсом `log(event, message)`.
- **Обратная совместимость**: сохранён «кортежный» API
  `extract_text()` / `extract_text_from_bytes()` → `(text, error)`.

---

## Поддерживаемые форматы

Сервис рассчитан на список из `file_formats.txt` (~175 форматов). Покрытие
организовано так: для большинства форматов есть нативное извлечение; XML- и
plain-text-семейства покрываются обобщёнными хендлерами; проприетарные форматы
**распознаются** и возвращают понятную причину; растровые изображения и сканы
идут в OCR.

| Категория            | Форматы (расширения)                                   | Библиотека / способ        | Примечание |
|----------------------|--------------------------------------------------------|----------------------------|------------|
| PDF                  | `.pdf`                                                  | PyMuPDF (`fitz`)           | Нет текста → OCR |
| Фикс. макет / e-book | `.xps`, `.oxps`, `.fb2`, `.mobi`, `.azw`, `.azw3`, `.cbz` | PyMuPDF                   | CBZ (картинки) → OCR |
| Word                 | `.docx`, `.docm`, `.dotx`; `.doc`, `.dot`              | python-docx / LibreOffice  | бинарные → `soffice` |
| Excel                | `.xlsx`, `.xlsm`, `.xls`, `.xlsb`                       | pandas + openpyxl/xlrd/pyxlsb | Все листы |
| PowerPoint           | `.pptx`, `.pptm`; `.ppt`                                | python-pptx / LibreOffice  | Слайды, таблицы, заметки |
| OpenDocument         | `.odt`, `.ods`, `.odp`, `.odg`, `.odf`                  | odfpy                      | |
| RTF                  | `.rtf`                                                  | striprtf                   | |
| HTML / web-архив     | `.html`, `.htm`, `.xhtml`, `.mht`, `.mhtml`             | beautifulsoup4 (+lxml)     | MHTML — HTML-часть |
| XML-семейство        | `.xml`, `.svg`, `.xliff`/`.xlf`, `.tmx`, `.dita`/`.ditamap`, `.docbook`, `.wsdl`, `.xsd`, `.dtd`, `.plist`, `.resx`/`.resw`, `.manifest`, `.fodt`/`.fods`/`.fodp` | stdlib | Текст всех элементов |
| EPUB                 | `.epub`                                                 | EbookLib + bs4 (резерв zip)| |
| E-mail               | `.eml`, `.msg`                                          | stdlib / extract-msg       | Заголовки + тело |
| Jupyter              | `.ipynb`                                                | stdlib (JSON)              | markdown + код |
| JSON                 | `.json`, `.jsonl`, `.ndjson`, `.arb`, `.swagger`, `.openapi` | stdlib               | Строковые значения и ключи |
| YAML                 | `.yaml`, `.yml`                                         | PyYAML (резерв — текст)    | |
| CSV / TSV            | `.csv`, `.tsv`                                          | stdlib                     | Автоопределение разделителя |
| Текст / разметка     | `.txt`, `.md`, `.markdown`, `.rst`, `.asciidoc`/`.adoc`, `.tex`/`.latex`, `.org`, `.rmd`, `.qmd`, `.log`, `.nfo`, `.ini`/`.cfg`/`.conf`/`.env`/`.properties`/`.toml` | stdlib | Plain-text |
| Субтитры / переводы  | `.srt`, `.vtt`, `.ass`, `.ssa`, `.sub`, `.lrc`, `.po`, `.pot`, `.strings` | stdlib | Plain-text |
| Исходный код         | `.py`, `.js`/`.mjs`/`.cjs`, `.ts`/`.tsx`/`.jsx`, `.java`, `.c`/`.h`/`.cpp`/`.cc`/`.hpp`, `.cs`, `.go`, `.rs`, `.rb`, `.php`, `.swift`, `.kt`/`.kts`, `.scala`, `.r`, `.m`, `.lua`, `.sh`/`.bash`/`.zsh`, `.ps1`, `.bat`/`.cmd`, `.pl`/`.pm`, `.ex`/`.exs`, `.erl`/`.hrl`, `.hs`/`.lhs`, `.clj`/`.cljs`, `.sql`, `.graphql`/`.gql`, `.proto`, `.dart`, `.vue`, `.svelte` | stdlib | Как plain-text |
| PIM                  | `.ics`, `.vcf`                                          | stdlib                     | Календарь / контакты |
| Базы данных          | `.sqlite`, `.sqlite3`, `.db`                            | stdlib `sqlite3`           | Таблицы/строки |
| Колоночные данные    | `.parquet`, `.feather`, `.arrow`, `.orc`, `.avro`       | pandas/pyarrow, fastavro   | |
| Архивы               | `.zip`, `.tar`, `.tar.gz`/`.tgz`, `.tar.bz2`/`.tbz2`, `.tar.xz`, `.gz`, `.bz2`, `.xz`, `.zst`, `.lz4`, `.rar`, `.cbr`, `.7z`, `.cab`, `.iso` | stdlib / rarfile / py7zr / zstandard / lz4 / cabarchive / pycdlib | Рекурсивно по содержимому |
| iWork                | `.key`, `.pages`, `.numbers`                            | zip + PDF-предпросмотр     | best-effort, иначе OCR |
| DjVu                 | `.djvu`, `.djv`                                         | `djvutxt` (CLI)            | иначе → OCR |
| PostScript           | `.ps`, `.eps`, `.ai`                                    | Ghostscript / PyMuPDF      | best-effort |
| Photoshop            | `.psd`                                                  | psd-tools                  | текстовые слои; иначе → OCR |
| Изображения          | `.png`, `.jpg`/`.jpeg`, `.tif`/`.tiff`, `.bmp`, `.gif`, `.webp`, `.heic`/`.heif`, `.avif`, `.jxl`, `.jp2`/`.j2k`, `.pnm`/`.pbm`/`.pgm`/`.ppm`, `.ico` | — | Нет текстового слоя → OCR |
| Распознаны, но н/д   | `.one`/`.onenote`, `.indd`, `.lit`, `.lrf`, `.pdb`, `.dmg` | —                       | Понятная причина, без извлечения |

> Полный плоский перечень — в разделе [Итоговый список форматов](#итоговый-список-форматов).

---

## Архитектура

```
                ┌──────────────────────────┐
   файл ──────▶ │   FileTextExtractor       │  фасад / точка входа
 (path|bytes)   │   (facade.py)             │
                └───────────┬──────────────┘
                            │ 1. MIME (mime_detect.py)
                            │ 2. текст. слой? (text_layer.py)
                            ▼
                ┌──────────────────────────┐
                │   ExtractorRegistry        │  выбор первого подходящего
                │   (registry.py)            │  экстрактора по can_handle()
                └───────────┬──────────────┘
                            ▼
        ┌───────────────────────────────────────────┐
        │   handlers/*  (BaseExtractor)               │
        │   pdf, docx, doc, excel, pptx, odf, rtf,    │
        │   html, xml, csv, json/yaml, epub, email,   │
        │   image, archives, plain_text               │
        └───────────────────┬───────────────────────┘
                            │ если needs_ocr / NO_TEXT_LAYER
                            ▼
                ┌──────────────────────────┐
                │   OcrEngine (ocr.py)       │  заглушка OcrStub
                └──────────────────────────┘
```

Ключевые абстракции (`interfaces.py`):

- **`Extractor`** — `can_handle(mime, filename)` + `extract(src) -> ExtractionResult`.
- **`MimeDetector`** — `detect(src) -> mime`.
- **`OcrEngine`** — `recognize(src) -> ExtractionResult` (для файлов без текстового слоя).

`BaseExtractor` (`handlers/base.py`) даёт общую реализацию `can_handle` по
объявленным `MIME_TYPES`/`EXTENSIONS`, а также `read_bytes` / `decode_bytes` /
`read_text` / ленивый `require()` для подключения опциональных зависимостей.

---

## Конвейер обработки

1. **Определение MIME** — по сигнатуре OOXML, затем libmagic, затем расширение.
2. **Предпроверка текстового слоя** — изображения сразу уходят в OCR.
3. **Выбор экстрактора** — первый, чей `can_handle` вернул `True`
   (порядок задаётся в `bootstrap.py`: архивы → документы → структурированные →
   изображения → plain-text).
4. **Извлечение** — экстрактор возвращает `ExtractionResult`.
5. **Постпроверка** — если экстрактор сообщил `needs_ocr` (например, PDF-скан),
   фасад вызывает OCR.

---

## Проверка текстового слоя и OCR

«Текстовый слой» — это текст, который можно извлечь **без распознавания**.

- **Заведомо без текста** (изображения) определяются на шаге 2 — функция
  `text_layer.definitely_needs_ocr`.
- **Контекстно без текста** (PDF-скан, пустой документ) определяется внутри
  хендлера: он возвращает `ExtractionResult.no_text_layer()`
  (`status=NO_TEXT_LAYER`, `needs_ocr=True`).

В обоих случаях фасад вызывает `OcrEngine`. Сейчас подключена заглушка
**`OcrStub`**, которая не распознаёт текст, а возвращает корректный результат с
кодом `OCR_NOT_IMPLEMENTED` и `needs_ocr=True`. Чтобы подключить настоящий OCR:

```python
from extractors import build_default_extractor, OcrEngine, ExtractionResult, FileSource

class TesseractOcr(OcrEngine):
    def recognize(self, src: FileSource) -> ExtractionResult:
        text = my_tesseract(src)            # ваша реализация
        return ExtractionResult.success(text, meta={"ocr": "tesseract"})

extractor = build_default_extractor(ocr=TesseractOcr())
```

Если OCR-движок не передать, по умолчанию используется `OcrStub`. Передача
`ocr=None` фактически означает «вернуть статус `NO_TEXT_LAYER` без распознавания».

---

## Установка

Пакет ставится стандартно через `pip` (src-layout, `pyproject.toml`). Ядро
тянет только `pydantic` и `charset-normalizer`; всё, что зависит от формата,
подключается через extras.

```bash
# из корня репозитория — для разработки (editable)
pip install -e .

# или из GitHub
pip install "extractors @ git+https://github.com/kestrel476/extractors.git"

# со всеми форматами
pip install -e ".[all]"

# только нужные группы форматов
pip install -e ".[pdf,office,markdown]"
```

Группы extras: `mime`, `pdf`, `office`, `data`, `web`, `email`, `markdown`,
`archives`, `misc`, `all` (см. `pyproject.toml`). После установки доступны
команда `extractors` и импорт `import extractors`.

Опциональные системные зависимости:

- **LibreOffice** (`soffice`) — для `.doc` и `.ppt`: `apt-get install libreoffice`
- **unrar** — для `.rar` (используется `rarfile`)

Любую опциональную библиотеку можно не ставить: соответствующий формат вернёт
`DEPENDENCY_MISSING`, остальные продолжат работать.

---

## Использование

```python
from extractors import build_default_extractor, FileSource

extractor = build_default_extractor()

# 1) Кортежный API (обратная совместимость)
text, error = extractor.extract_text("/path/to/document.pdf")
text, error = extractor.extract_text_from_bytes("report.docx", data_bytes)

# 2) Богатый API
result = extractor.extract(FileSource(path="/path/to/document.pdf"))
if result.ok and result.text:
    print(result.text)
elif result.needs_ocr:
    print("Нет текстового слоя — требуется OCR")
else:
    print("Ошибка:", result.error, result.meta.get("code"))

# 3) Markdown-режим — читает документ в Markdown с сохранением таблиц
#    (для подачи в LLM). meta['format'] == 'markdown', если структура сохранена.
result = extractor.extract(FileSource(path="/path/to/report.docx"), markdown=True)
# то же самое: extractor.extract_markdown(FileSource(path=...))
print(result.text)  # заголовки, абзацы и Markdown-таблицы
```

Включение логирования:

```python
from extractors import build_default_extractor, get_logger
extractor = build_default_extractor(logger=get_logger(enabled=True))
```

---

## CLI

После установки доступна команда `extractors` (эквивалент `python -m extractors`).
Принимает путь к файлу **или каталогу**.

```bash
# один файл, человекочитаемый вывод
extractors document.pdf

# Markdown-режим (таблицы сохраняются; для подачи в LLM)
extractors report.docx --md

# полный результат в JSON (text, status, needs_ocr, meta, warnings)
extractors document.docx --json

# каталог рекурсивно + сводка по статусам
extractors ./inbox --recursive

# подробное логирование шагов конвейера
extractors scan.pdf --verbose
```

| Флаг | Назначение |
|------|-----------|
| `-r`, `--recursive` | обходить каталог рекурсивно |
| `--md`, `--markdown` | Markdown-режим (сохраняет таблицы) |
| `--json` | полный `ExtractionResult` в JSON |
| `--preview N` | длина превью текста (`0` — без ограничения) |
| `--pdf-max-pages N` | лимит страниц PDF |
| `--verbose` | подробное логирование |

---

## Markdown-режим (`--md` / `markdown=True`)

Обычный режим извлекает «плоский» текстовый слой, при этом табличная разметка
теряется. Markdown-режим возвращает документ в **Markdown с сохранением таблиц**,
что удобно для подачи в LLM. Включается флагом `--md` в CLI или параметром
`extract(src, markdown=True)` (есть и обёртка `extract_markdown(src)`).

Стратегия трёхуровневая:

1. **markitdown** — для форматов, где библиотека даёт качественный Markdown:
   `docx/docm/dotx`, `xlsx/xls`, `pptx/pptm`, `pdf`, `html/htm/xhtml`, `epub`,
   `ipynb`, Outlook `.msg`.
2. **Нативные md-рендеры** — для табличных форматов, которые markitdown не
   покрывает: OpenDocument (`odt/ods/odp`), RTF, `csv/tsv`, SQLite, колоночные
   данные (`parquet/feather/orc/avro`), `xlsm/xlsb`. Строят настоящие
   Markdown-таблицы.
3. **Passthrough** — для plain-text, кода, разметки, XML/JSON текст и так является
   валидным Markdown, поэтому возвращается как есть (`meta['format'] == 'text'`).

Архивы (`zip/tar/rar/7z/…`) распаковываются, и каждый вложенный файл проходит
тот же конвейер: в md-режиме содержимое рекурсивно рендерится в Markdown под
заголовком `# <имя файла>`.

Мягкая деградация: если `markitdown` не установлен или не смог сконвертировать
файл, режим откатывается на нативный путь (текст вместо Markdown), а не падает.
В `meta` проставляется `format` (`markdown`/`text`) и `renderer` (`markitdown`).
Файлы без текстового слоя (сканы) в md-режиме так же уходят в OCR.

Установка зависимости режима: `pip install "markitdown[all]"`.

---

## Модель результата

`ExtractionResult` (`types.py`):

| Поле        | Тип               | Описание |
|-------------|-------------------|----------|
| `text`      | `str \| None`     | Извлечённый текст |
| `error`     | `str \| None`     | Человекочитаемое описание ошибки |
| `status`    | `ExtractionStatus`| `ok` / `no_text_layer` / `unsupported` / `error` |
| `needs_ocr` | `bool`            | Требуется OCR |
| `meta`      | `dict[str,str]`   | `code`, `pages`, `encoding`, `sheets`, `entries`, … |
| `warnings`  | `list[str]`       | Некритичные предупреждения (усечение, fallback кодировки) |

Свойства: `result.ok` (нет ошибки), `result.failed` (есть ошибка).
Фабрики: `ExtractionResult.success(...)`, `.failure(...)`, `.no_text_layer(...)`.

---

## Коды ошибок и статусы

`ErrorCodes` (`errors.py`), попадают в `meta["code"]`:

| Код                   | Когда |
|-----------------------|-------|
| `UNSUPPORTED_FORMAT`  | Нет экстрактора для формата |
| `READ_ERROR`          | Ошибка открытия/чтения файла |
| `ENCODING_ERROR`      | Не удалось определить кодировку |
| `PARSE_ERROR`         | Ошибка разбора (битый XML/JSON/CSV) |
| `NO_TEXT_LAYER`       | Нет текстового слоя |
| `OCR_NOT_IMPLEMENTED` | Вызван OCR, но подключена заглушка |
| `DEPENDENCY_MISSING`  | Не установлена опциональная библиотека |
| `TOO_LARGE`           | Превышен лимит размера (архив/файл) |
| `ARCHIVE_PASSWORD`    | Архив зашифрован |
| `ARCHIVE_NO_CANDIDATE`| В архиве нет извлекаемых файлов |
| `ARCHIVE_ERROR`       | Прочие ошибки архива |
| `EMPTY`               | Формат распознан, но текста нет |

---

## Как добавить новый формат

1. Создайте `handlers/<format>.py`, унаследуйте `BaseExtractor`:

```python
from .base import BaseExtractor
from ..types import ExtractionResult, FileSource

class MyExtractor(BaseExtractor):
    MIME_TYPES = frozenset({"application/x-my"})
    EXTENSIONS = (".my",)

    def extract(self, src: FileSource) -> ExtractionResult:
        try:
            lib = self.require("mylib", pip_name="mylib")
        except ImportError as e:
            return self.dependency_error(e)
        text, enc, warnings = self.read_text(src)   # для текстовых форматов
        return ExtractionResult.success(text, meta={"encoding": enc}, warnings=warnings)
```

2. Зарегистрируйте в `bootstrap.py` (с учётом порядка — специфичное раньше общего).
3. При необходимости добавьте расширение/MIME в `mime_detect.EXT_TO_MIME`.

---

## Структура проекта

```
extractors/                  # корень репозитория
├── pyproject.toml           # метаданные пакета, зависимости, extras, команда
├── README.md
├── docs/
│   └── supported-formats.md # полный перечень целевых форматов
└── src/
    └── extractors/          # пакет (import extractors)
        ├── __init__.py      # публичный API + __version__
        ├── __main__.py      # python -m extractors → cli.main
        ├── cli.py           # CLI (команда `extractors`)
        ├── py.typed         # маркер типизации (PEP 561)
        ├── _logging.py      # встроенный логгер-шим (NullLogger/StdLogger)
        ├── types.py         # FileSource, ExtractionResult, ExtractionStatus
        ├── interfaces.py    # Extractor, MimeDetector, OcrEngine
        ├── errors.py        # ErrorCodes
        ├── registry.py      # ExtractorRegistry
        ├── mime_detect.py   # MagicMimeDetector + карта расширений (~175)
        ├── text_layer.py    # проверка наличия текстового слоя
        ├── ocr.py           # OcrStub (заглушка OCR)
        ├── facade.py        # FileTextExtractor (конвейер, в т.ч. md-режим)
        ├── markdown_render.py # MarkItDownRenderer (markitdown, Тир 1 md-режима)
        ├── bootstrap.py     # build_default_extractor() — сборка реестра
        └── handlers/
            ├── base.py          # BaseExtractor (общая логика + extract_markdown)
            ├── _markdown.py     # сборка Markdown-таблиц для нативных md-рендеров
            ├── _soffice.py      # конвертация через LibreOffice (doc/ppt)
            ├── pdf.py · fitz_doc.py        # PDF; XPS/FB2/MOBI/CBZ через MuPDF
            ├── docx.py · doc.py
            ├── excel.py · powerpoint.py · opendocument.py
            ├── rtf.py · html.py · xml.py
            ├── csv_tsv.py · structured.py  # CSV/TSV; JSON/YAML
            ├── web_docs.py                 # .ipynb, .mht/.mhtml
            ├── epub.py · email_msg.py
            ├── data.py                     # SQLite; Parquet/Feather/ORC/Avro
            ├── pim.py                      # .ics/.vcf
            ├── iwork.py                    # .key/.pages/.numbers
            ├── best_effort.py              # DjVu, PostScript, PSD
            ├── recognized.py               # распознаны, но н/д
            ├── image.py
            └── archives.py
```

### Точки входа

- **Команда `extractors`** (`src/extractors/cli.py`) — ставится вместе с пакетом,
  принимает файл или каталог; эквивалент `python -m extractors`.
- **Программно** — через `build_default_extractor()` (см. [Использование](#использование)).

```bash
extractors document.pdf            # один файл
extractors ./inbox --recursive     # каталог рекурсивно + сводка по статусам
extractors report.docx --md        # Markdown с таблицами
extractors scan.pdf --verbose      # с логами конвейера
```

---

## Заметки по миграции

По сравнению с исходной версией:

- Пакет сделан **автономным**: убрана зависимость от внешнего
  `src.core.custom_logger` и абсолютных импортов `src.core.extractors.*` —
  везде относительные импорты и встроенный логгер.
- Исправлены опечатки в API: `can_handler → can_handle`,
  `MimeDerector → MimeDetector`.
- Единый `BaseExtractor` устранил дублирование чтения байтов и определения
  кодировки в 5 хендлерах; логирование стало лаконичным (без записи каждого
  параграфа/строки).
- Унифицирован результат через фабрики `ExtractionResult.success/failure/no_text_layer`,
  добавлены поля `status` и `needs_ocr`.
- Исправлен баг `ArchiveExtractor.can_handle`, который перехватывал файлы без
  имени; архивы теперь обрабатываются рекурсивно по всем вложенным файлам, а не
  по одному «кандидату»; увеличен таймаут конвертации LibreOffice.

### Итоговый список форматов

**Извлекается нативно:**
- **Офис:** docx, docm, dotx, doc, dot, xlsx, xlsm, xlsb, xls, pptx, pptm, ppt
- **OpenDocument:** odt, ods, odp, odg, odf
- **PDF/макет/e-book:** pdf, xps, oxps, fb2, mobi, azw, azw3, cbz, epub
- **RTF:** rtf
- **Web/разметка:** html, htm, xhtml, mht, mhtml, xml, svg, xliff, xlf, tmx, dita,
  ditamap, docbook, wsdl, xsd, dtd, plist, resx, resw, manifest, fodt, fods, fodp
- **Данные/структуры:** json, jsonl, ndjson, arb, swagger, openapi, ipynb, yaml,
  yml, csv, tsv, parquet, feather, arrow, orc, avro, sqlite, sqlite3, db
- **Почта/PIM:** eml, msg, ics, vcf
- **Текст/разметка:** txt, text, md, markdown, rst, asciidoc, adoc, tex, latex,
  org, rmd, qmd, log, nfo, me, 1st, ini, cfg, conf, env, properties, toml
- **Субтитры/переводы:** srt, vtt, ass, ssa, sub, lrc, po, pot, strings
- **Исходный код:** py, rs, js, mjs, cjs, ts, tsx, jsx, vue, svelte, java, c, h,
  cpp, cc, cxx, hpp, cs, go, rb, php, swift, kt, kts, scala, r, m, lua, sh, bash,
  zsh, ps1, bat, cmd, pl, pm, ex, exs, erl, hrl, hs, lhs, clj, cljs, sql, graphql,
  gql, proto, dart
- **Архивы (рекурсивно):** zip, tar, tar.gz, tgz, tar.bz2, tbz2, tar.xz, gz, bz2,
  xz, zst, lz4, rar, cbr, 7z, cab, iso, а также sketch (zip+json)

**Best-effort (зависят от внешнего инструмента/библиотеки):**
- iWork: key, pages, numbers (через PDF-предпросмотр) · DjVu: djvu, djv (`djvutxt`) ·
  PostScript: ps, eps, ai (Ghostscript/MuPDF) · Photoshop: psd (текстовые слои)

**Без текстового слоя → OCR:** png, jpg, jpeg, tif, tiff, bmp, gif, webp, heic,
heif, avif, jxl, jp2, j2k, pnm, pbm, pgm, ppm, ico (а также сканы PDF/XPS/DjVu и
iWork/PSD без текста).

**Распознаются, но извлечение не поддерживается** (проприетарные/закрытые,
возвращается понятная причина): one, onenote, indd, lit, lrf, pdb, dmg.
