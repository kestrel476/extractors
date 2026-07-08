# Поддерживаемые форматы

Сервис нацелен на ~175 форматов. Для большинства есть нативное извлечение;
XML- и plain-text-семейства покрываются обобщёнными хендлерами; проприетарные
форматы распознаются с понятной причиной; растровые изображения и сканы идут в OCR.

> Сгенерировано из исторического `file_formats.txt`. Детали покрытия и используемых
> библиотек — в таблице «Поддерживаемые форматы» в [`README.md`](../README.md).

## ОФИСНЫЕ ДОКУМЕНТЫ (Microsoft Office)

| Расширение | Описание |
|---|---|
| `.docx` | Word (XML-based) |
| `.doc` | Word (старый бинарный) |
| `.docm` | Word с макросами |
| `.dotx` | Шаблон Word (XML) |
| `.dot` | Шаблон Word (старый) |
| `.xlsx` | Excel (XML-based) |
| `.xls` | Excel (старый бинарный) |
| `.xlsm` | Excel с макросами |
| `.xlsb` | Excel бинарный |
| `.pptx` | PowerPoint (XML-based) |
| `.ppt` | PowerPoint (старый бинарный) |
| `.pptm` | PowerPoint с макросами |
| `.onenote` | Microsoft OneNote |
| `.one` | Microsoft OneNote (секция) |
| `.msg` | Outlook письмо |
| `.eml` | Email (стандартный формат) |
| `.mht` | Web Archive (IE/Outlook) |
| `.mhtml` | Web Archive (IE/Outlook) |

## OPENDOCUMENT (LibreOffice / OpenOffice)

| Расширение | Описание |
|---|---|
| `.odt` | Текстовый документ |
| `.ods` | Таблица |
| `.odp` | Презентация |
| `.odg` | Графика (с текстовыми объектами) |
| `.odf` | Формулы |
| `.fodt` | Flat XML текст |
| `.fods` | Flat XML таблица |
| `.fodp` | Flat XML презентация |

## PDF И ФИКСИРОВАННЫЕ МАКЕТЫ

| Расширение | Описание |
|---|---|
| `.pdf` | PDF (цифровой слой или OCR) |
| `.xps` | XML Paper Specification |
| `.oxps` | Open XPS |
| `.djvu` | DjVu |
| `.djv` | DjVu (альтернативное расширение) |

## ИЗОБРАЖЕНИЯ (только через OCR)

*→ OCR (нет текстового слоя)*

| Расширение | Описание |
|---|---|
| `.png` | PNG |
| `.jpg` | JPEG |
| `.jpeg` | JPEG |
| `.tiff` | TIFF (часто сканы документов) |
| `.tif` | TIFF |
| `.bmp` | BMP |
| `.webp` | WebP |
| `.gif` | GIF |
| `.heic` | Apple HEIC |
| `.heif` | Apple HEIF |
| `.avif` | AVIF |
| `.jxl` | JPEG XL |
| `.jp2` | JPEG 2000 |
| `.j2k` | JPEG 2000 |
| `.pnm` | Portable bitmap |
| `.pbm` | Portable bitmap (чёрно-белый) |
| `.pgm` | Portable bitmap (серый) |
| `.ppm` | Portable bitmap (цветной) |
| `.ico` | Иконки |
| `.svg` | SVG (текст прямо в XML) |

## ТЕКСТОВЫЕ И РАЗМЕТОЧНЫЕ ФОРМАТЫ

| Расширение | Описание |
|---|---|
| `.txt` | Простой текст |
| `.md` | Markdown |
| `.markdown` | Markdown |
| `.rst` | reStructuredText |
| `.asciidoc` | AsciiDoc |
| `.adoc` | AsciiDoc |
| `.tex` | LaTeX |
| `.latex` | LaTeX |
| `.org` | Org-mode (Emacs) |
| `.rtf` | Rich Text Format |
| `.csv` | CSV |
| `.tsv` | TSV |
| `.log` | Лог-файлы |
| `.nfo` | NFO (CP437/ASCII art) |
| `.me` | Read-me файл |
| `.1st` | Read-me файл |

## WEB / РАЗМЕТКА

| Расширение | Описание |
|---|---|
| `.html` | HTML |
| `.htm` | HTML |
| `.xhtml` | XHTML |
| `.xml` | XML |
| `.json` | JSON |
| `.jsonl` | JSON Lines |
| `.ndjson` | Newline-delimited JSON |
| `.yaml` | YAML |
| `.yml` | YAML |
| `.toml` | TOML |
| `.ini` | Конфигурационный файл |
| `.cfg` | Конфигурационный файл |
| `.conf` | Конфигурационный файл |
| `.env` | Environment файл |
| `.properties` | Java properties |

## ИСХОДНЫЙ КОД

| Расширение | Описание |
|---|---|
| `.py` | Python |
| `.rs` | Rust |
| `.js` | JavaScript |
| `.mjs` | JavaScript (ES module) |
| `.cjs` | JavaScript (CommonJS) |
| `.ts` | TypeScript |
| `.java` | Java |
| `.c` | C |
| `.h` | C заголовочный файл |
| `.cpp` | C++ |
| `.cc` | C++ |
| `.cxx` | C++ |
| `.hpp` | C++ заголовочный файл |
| `.cs` | C# |
| `.go` | Go |
| `.rb` | Ruby |
| `.php` | PHP |
| `.swift` | Swift |
| `.kt` | Kotlin |
| `.kts` | Kotlin script |
| `.scala` | Scala |
| `.r` | R |
| `.m` | MATLAB / Objective-C |
| `.lua` | Lua |
| `.sh` | Shell-скрипт |
| `.bash` | Bash-скрипт |
| `.zsh` | Zsh-скрипт |
| `.ps1` | PowerShell |
| `.bat` | Windows batch |
| `.cmd` | Windows batch |
| `.pl` | Perl |
| `.pm` | Perl module |
| `.ex` | Elixir |
| `.exs` | Elixir script |
| `.erl` | Erlang |
| `.hrl` | Erlang заголовочный файл |
| `.hs` | Haskell |
| `.lhs` | Haskell (literate) |
| `.clj` | Clojure |
| `.cljs` | ClojureScript |
| `.sql` | SQL |
| `.graphql` | GraphQL |
| `.gql` | GraphQL |
| `.proto` | Protocol Buffers |
| `.dart` | Dart |
| `.vue` | Vue.js |
| `.jsx` | React JSX |
| `.tsx` | React TSX |
| `.svelte` | Svelte |

## ЭЛЕКТРОННЫЕ КНИГИ

| Расширение | Описание |
|---|---|
| `.epub` | EPUB |
| `.mobi` | Mobipocket |
| `.azw` | Amazon Kindle |
| `.azw3` | Amazon Kindle (KF8) |
| `.fb2` | FictionBook (XML) |
| `.lit` | Microsoft LIT |
| `.lrf` | Sony Reader |
| `.pdb` | Palm Database |
| `.cbz` | Comic Book ZIP |
| `.cbr` | Comic Book RAR |

## АРХИВЫ (требуют распаковки перед извлечением)

*распаковка + рекурсивная обработка вложенных файлов*

| Расширение | Описание |
|---|---|
| `.zip` | ZIP |
| `.rar` | RAR |
| `.7z` | 7-Zip |
| `.tar` | TAR |
| `.tar.gz` | TAR + Gzip |
| `.tgz` | TAR + Gzip |
| `.tar.bz2` | TAR + Bzip2 |
| `.tbz2` | TAR + Bzip2 |
| `.tar.xz` | TAR + XZ |
| `.gz` | Gzip (одиночный файл) |
| `.bz2` | Bzip2 |
| `.xz` | XZ |
| `.zst` | Zstandard |
| `.lz4` | LZ4 |
| `.cab` | Windows Cabinet |
| `.iso` | Образ диска |
| `.dmg` | macOS образ |

## ПРЕЗЕНТАЦИИ И ДИЗАЙН

| Расширение | Описание |
|---|---|
| `.key` | Apple Keynote |
| `.pages` | Apple Pages |
| `.numbers` | Apple Numbers |
| `.sketch` | Sketch (JSON внутри) |
| `.ai` | Adobe Illustrator (PostScript) |
| `.indd` | Adobe InDesign |
| `.psd` | Photoshop (текстовые слои) |
| `.eps` | Encapsulated PostScript |
| `.ps` | PostScript |

## БАЗЫ ДАННЫХ И ДАННЫЕ

| Расширение | Описание |
|---|---|
| `.sqlite` | SQLite |
| `.db` | SQLite / другие БД |
| `.sqlite3` | SQLite |
| `.parquet` | Apache Parquet |
| `.avro` | Apache Avro |
| `.orc` | Apache ORC |
| `.arrow` | Apache Arrow |
| `.feather` | Apache Arrow Feather |

## СПЕЦИАЛИЗИРОВАННЫЕ / ПРОЧЕЕ

| Расширение | Описание |
|---|---|
| `.ipynb` | Jupyter Notebook (JSON) |
| `.rmd` | R Markdown |
| `.qmd` | Quarto |
| `.pot` | Gettext шаблон переводов |
| `.po` | Gettext переводы |
| `.xliff` | Локализационный XML |
| `.xlf` | Локализационный XML |
| `.tmx` | Translation Memory Exchange |
| `.srt` | Субтитры SRT |
| `.vtt` | Субтитры WebVTT |
| `.ass` | Субтитры ASS |
| `.ssa` | Субтитры SSA |
| `.sub` | Субтитры SUB |
| `.lrc` | Тексты песен (LRC) |
| `.dita` | DITA документация |
| `.ditamap` | DITA карта документации |
| `.docbook` | DocBook XML |
| `.wsdl` | Web Services Description Language |
| `.xsd` | XML Schema Definition |
| `.dtd` | Document Type Definition |
| `.manifest` | Манифест |
| `.plist` | Apple Property List |
| `.resx` | .NET ресурсы |
| `.resw` | .NET ресурсы (Windows) |
| `.strings` | Apple локализация |
| `.arb` | Flutter локализация |
| `.ics` | Календарь (iCalendar) |
| `.vcf` | Контакт (vCard) |
| `.swagger` | Swagger / OpenAPI |
| `.openapi` | OpenAPI спецификация |
