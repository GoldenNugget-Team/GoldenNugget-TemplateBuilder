"""Russian interface text: English text → Russian.

A value that is a tuple holds the three Russian plural forms for 1, 2–4 and
5+ (see i18n.n_). {placeholders} stay as they are. Names of iOS folders,
files, keys and GoldenNugget's own terms (Managed Preferences, config.json,
$value) are not translated.
"""

RU = {
    # ----- loading and saving -----
    "The template is too large to open.": "Шаблон слишком большой, его нельзя открыть.",
    "The file has no config.json.": "В файле нет config.json.",
    "This is not a .batter file: {error}": "Это не файл .batter: {error}",
    "config.json is not valid JSON: {error}": "config.json содержит некорректный JSON: {error}",
    "{name} is outside the folder that holds config.json.": "{name} лежит вне папки с config.json.",
    "Unsafe file name in the template: {name}": "Небезопасное имя файла в шаблоне: {name}",

    # ----- plist import -----
    "data": "двоичные данные",
    "a date": "дата",
    "a number beyond the 32-bit range": "число вне 32-битного диапазона",
    "The plist holds no keys: its top level is not a dictionary.":
        "В plist нет ключей: на верхнем уровне у него не словарь.",
    "This is not a plist file: {error}": "Это не файл plist: {error}",

    # ----- the checks -----
    "GoldenNugget cannot write to this location.": "GoldenNugget не может записывать в это место.",
    "Paths must be absolute and start with /var/.": "Путь должен быть абсолютным и начинаться с /var/.",
    "Paths may not contain '..', '//' or a trailing slash.":
        "Путь не может содержать '..', '//' или заканчиваться косой чертой.",
    "This file is protected and cannot be changed by a template.":
        "Этот файл защищён, шаблон не может его менять.",
    "Plist values are nested too deeply.": "Значения plist вложены слишком глубоко.",
    "Plist keys must be text.": "Ключи plist должны быть текстом.",
    "Plist values cannot be null.": "Значения plist не могут быть null.",
    "High risk: writes into a system folder.": "Высокий риск: запись в системную папку.",
    "Low risk: keys in Managed Preferences.": "Низкий риск: ключи в Managed Preferences.",
    "Medium risk: the whole file is replaced and the iPhone's own copy is lost.":
        "Средний риск: файл заменяется целиком, и собственная копия iPhone теряется.",
    "control": "контрол",
    "\"$value\" is used but the tweak has no control, so it is written literally.":
        "Используется \"$value\", но у твика нет контрола, поэтому значение запишется как есть.",
    "Controls are slider, text or choice.": "Контрол бывает слайдером, текстом или списком.",
    "Slider limits must be numbers.": "Границы слайдера должны быть числами.",
    "A slider needs min below max and a positive step.":
        "У слайдера минимум должен быть меньше максимума, а шаг — положительным.",
    "The slider default is outside min and max; GoldenNugget clamps it.":
        "Значение слайдера по умолчанию вне границ; GoldenNugget подрежет его.",
    "max_length must be between 1 and 1000.": "max_length должен быть от 1 до 1000.",
    "A text default must be text.": "Текст по умолчанию должен быть текстом.",
    "The text default is longer than max_length; GoldenNugget cuts it.":
        "Текст по умолчанию длиннее max_length; GoldenNugget обрежет его.",
    "A choice needs between 1 and 50 choices.": "В списке должно быть от 1 до 50 вариантов.",
    "Choice {n} needs a label of at most 80 characters.":
        "Варианту {n} нужна подпись длиной не больше 80 символов.",
    "Choice {n}: {problem}": "Вариант {n}: {problem}",
    "A choice default is the index of a choice.": "Вариант по умолчанию — это номер варианта.",
    "The control's value is not used: put \"$value\" into a plist value.":
        "Значение контрола нигде не используется: подставьте \"$value\" в значение plist.",
    "Writes are plist, file or empty.": "Запись бывает plist, файлом или пустой.",
    "The owner is 501 (mobile) or 0 (root).": "Владелец — 501 (mobile) или 0 (root).",
    "A plist write needs at least one key.": "Записи plist нужен хотя бы один ключ.",
    "The path does not end in .plist.": "Путь не заканчивается на .plist.",
    "A file write needs a file inside the template.": "Записи файла нужен файл внутри шаблона.",
    "Missing file in template: {name}": "В шаблоне нет файла: {name}",
    "The file is larger than 4 MB.": "Файл больше 4 МБ.",
    "GoldenNugget writes this file itself; replacing it is refused while its own tweaks use it.":
        "GoldenNugget сам записывает этот файл; заменить его нельзя, пока его используют твики GoldenNugget.",
    "Tweak {n}": "Твик {n}",
    "The id uses letters, digits, '.', '_' or '-' (up to 64, starting with a letter or digit).":
        "Id состоит из латинских букв, цифр, '.', '_' или '-' (до 64 знаков, начинается с буквы или цифры).",
    "The id \"{id}\" is used twice.": "Id \"{id}\" встречается дважды.",
    "Every tweak needs a label of at most 80 characters.":
        "Каждому твику нужна подпись длиной не больше 80 символов.",
    "The description is longer than 500 characters.": "Описание длиннее 500 символов.",
    "iOS versions look like 18 or 18.4.": "Версии iOS записываются как 18 или 18.4.",
    "The minimum iOS version is above the maximum.": "Минимальная версия iOS больше максимальной.",
    "A tweak needs at least one write for when it is on.":
        "Твику нужна хотя бы одна запись для включённого состояния.",
    "A tweak has at most 32 writes.": "У твика может быть не больше 32 записей.",
    "on": "вкл",
    "off": "выкл",
    "write {n}": "запись {n}",
    "{path} is written both as plist keys and as a whole file.":
        "{path} записывается и как ключи plist, и как файл целиком.",
    "Template": "Шаблон",
    "The template needs a title.": "Шаблону нужно название.",
    "The template needs an author.": "Шаблону нужен автор.",
    "Up to 8 tags of at most 24 characters.": "До 8 тегов длиной не больше 24 символов.",
    "Add at least one tweak.": "Добавьте хотя бы один твик.",
    "A template has at most 64 tweaks.": "В шаблоне может быть не больше 64 твиков.",
    "The template has a Container folder but no domain.": "В шаблоне есть папка Container, но не указан domain.",
    "Files used by tweaks add up to more than 16 MB.": "Файлы твиков вместе занимают больше 16 МБ.",
    "{name} is not used by any tweak and will still be saved.":
        "{name} не используется ни одним твиком, но всё равно будет сохранён.",

    # ----- main window -----
    "GoldenNugget templates (*.batter)": "Шаблоны GoldenNugget (*.batter)",
    "Error": "Ошибка",
    "Warning": "Предупреждение",
    "Note": "Заметка",
    "The catalog shows the title, author, description, iOS range and tags. Each tweak becomes a switch in "
    "GoldenNugget's PosterBoard → Templates.":
        "Каталог показывает название, автора, описание, версии iOS и теги. Каждый твик становится "
        "переключателем в GoldenNugget: PosterBoard → Templates.",
    "Details": "Сведения",
    "your name": "ваше имя",
    "What the template changes. Name every file it writes outside Managed Preferences.":
        "Что меняет шаблон. Перечислите все файлы, которые он пишет вне Managed Preferences.",
    "Title": "Название",
    "Author": "Автор",
    "Description": "Описание",
    "iOS": "iOS",
    "Tags": "Теги",
    "Files": "Файлы",
    "Remove Unused Files": "Удалить неиспользуемые файлы",
    "No files yet. A tweak's Whole file write adds one.":
        "Файлов пока нет. Их добавляет запись твика «Файл целиком».",
    "{size} bytes": "{size} байт",
    "unused": "не используется",
    "Check": "Проверка",
    "Ready": "Готово",
    "The same checks GoldenNugget runs when it loads the template, plus the risk notes its apply summary "
    "shows. Double-click a line to open the tweak.":
        "Те же проверки, что GoldenNugget выполняет при загрузке шаблона, и оценки риска из его сводки "
        "перед применением. Двойной щелчок по строке открывает твик.",
    "Problems and notes": "Проблемы и заметки",
    "Where": "Где",
    "Problem": "Проблема",
    "{n} error": ("{n} ошибка", "{n} ошибки", "{n} ошибок"),
    "{n} warning": ("{n} предупреждение", "{n} предупреждения", "{n} предупреждений"),
    "&File": "&Файл",
    "New": "Новый",
    "Open…": "Открыть…",
    "Save": "Сохранить",
    "Save As…": "Сохранить как…",
    "Open Recent": "Недавние",
    "Quit": "Выход",
    "&Edit": "&Правка",
    "Undo": "Отменить",
    "Redo": "Повторить",
    "&Tweak": "&Твик",
    "Add Tweak": "Добавить твик",
    "Duplicate Tweak": "Дублировать твик",
    "Move Up": "Выше",
    "Move Down": "Ниже",
    "Remove Tweak…": "Удалить твик…",
    "&View": "&Вид",
    "Appearance": "Оформление",
    "Same as System": "Как в системе",
    "Light": "Светлое",
    "Dark": "Тёмное",
    "Language": "Язык",
    "&Catalog": "&Каталог",
    "Submit to Catalog…": "Отправить в каталог…",
    "&Help": "&Справка",
    "Guided Tour": "Обзорный тур",
    "Template Format Guide": "Описание формата шаблонов",
    "Check for Updates…": "Проверить обновления…",
    "Check for Updates Automatically": "Проверять обновления автоматически",
    "About": "О программе",
    "Submit to Catalog": "Отправить в каталог",
    "No tweaks yet": "Твиков пока нет",
    "A tweak is a switch in GoldenNugget that writes plist keys or files on the iPhone.":
        "Твик — это переключатель в GoldenNugget, который записывает ключи plist или файлы на iPhone.",
    "Check and Preview": "Проверка и config.json",
    "iPhone Preview": "Превью на iPhone",
    "Tweaks": "Твики",
    "(no label)": "(без подписи)",
    "Untitled": "Без названия",
    "Not saved yet": "Ещё не сохранён",
    "(copy)": "(копия)",
    "this tweak": "этот твик",
    "Remove Tweak": "Удалить твик",
    "Remove {name}?": "Удалить «{name}»?",
    "Removed {n} unused file": ("Удалён {n} неиспользуемый файл", "Удалено {n} неиспользуемых файла",
                                "Удалено {n} неиспользуемых файлов"),
    "Unsaved Changes": "Несохранённые изменения",
    "Save the changes to this template first?": "Сначала сохранить изменения в этом шаблоне?",
    "Clear Menu": "Очистить список",
    "No recent templates": "Недавних шаблонов нет",
    "Cannot Open": "Не удаётся открыть",
    "{path} no longer exists.": "{path} больше не существует.",
    "Open Template": "Открыть шаблон",
    "Save Template": "Сохранить шаблон",
    "The template has {n} error.": ("В шаблоне {n} ошибка.", "В шаблоне {n} ошибки.", "В шаблоне {n} ошибок."),
    "GoldenNugget refuses to load it until they are fixed.":
        "GoldenNugget не загрузит его, пока они не исправлены.",
    "Save Anyway": "Всё равно сохранить",
    "Show Problems": "Показать проблемы",
    "Cannot Save": "Не удаётся сохранить",
    "Fix the {n} error on the Check page first.": ("Сначала исправьте {n} ошибку на странице «Проверка».",
                                                   "Сначала исправьте {n} ошибки на странице «Проверка».",
                                                   "Сначала исправьте {n} ошибок на странице «Проверка»."),
    "GoldenNugget would refuse this template.": "GoldenNugget не примет этот шаблон.",
    "Catalog id (the file name: lowercase letters, digits and dashes):":
        "Id в каталоге (имя файла: строчные латинские буквы, цифры и дефисы):",
    "Use 2–48 lowercase letters, digits and dashes, for example dock-tweaks.":
        "Используйте 2–48 строчных латинских букв, цифр и дефисов, например dock-tweaks.",
    "Where to save the file to upload": "Куда сохранить файл для загрузки",
    "{path} exists. Replace it?": "{path} уже существует. Заменить?",
    "The catalog accepts templates of at most 25 MB; this one is {size} MB.":
        "Каталог принимает шаблоны до 25 МБ, а этот занимает {size} МБ.",
    "Saved {name}.batter and opened GitHub.\n\n1. Drag the file onto the GitHub page.\n2. Click Propose "
    "changes, then Create pull request.\n\nGitHub makes a copy (fork) of the catalog for you if you need one. "
    "A check lists every file your tweaks write, and the team reviews it before it appears in GoldenNugget.":
        "Файл {name}.batter сохранён, GitHub открыт.\n\n1. Перетащите файл на страницу GitHub.\n2. Нажмите "
        "Propose changes, затем Create pull request.\n\nGitHub при необходимости сам сделает вам копию (fork) "
        "каталога. Проверка перечислит все файлы, которые пишут ваши твики, а команда просмотрит шаблон, "
        "прежде чем он появится в GoldenNugget.",
    "Saved {name}": "Сохранено: {name}",
    "Builds GoldenNugget .batter templates with community tweaks (format 3) and checks them with "
    "GoldenNugget's rules.":
        "Создаёт шаблоны .batter для GoldenNugget с твиками сообщества (формат 3) и проверяет их по "
        "правилам GoldenNugget.",
    "Controls: awesomeUI.": "Элементы интерфейса: awesomeUI.",
    "The new language is used after a restart of {app}.": "Новый язык включится после перезапуска {app}.",
    "an unsaved template": "несохранённом шаблоне",
    "Restore Unsaved Changes": "Восстановить несохранённые изменения",
    "{app} closed last time without saving the changes to {name}. Restore them?":
        "В прошлый раз {app} закрылся, не сохранив изменения в {name}. Восстановить их?",
    "Version {version} is available": "Доступна версия {version}",
    "Check for Updates": "Проверка обновлений",
    "Could not reach GitHub: {error}": "Не удалось связаться с GitHub: {error}",
    "{app} {version} is available (this is {current}). Open the download page?":
        "Доступен {app} {version} (у вас {current}). Открыть страницу загрузки?",
    "{app} {version} is the latest version.": "{app} {version} — последняя версия.",
    "GitHub's answer is not JSON: {error}": "Ответ GitHub — не JSON: {error}",
    "GitHub's answer has no release version.": "В ответе GitHub нет версии релиза.",

    # ----- small parts -----
    "any": "любая",
    "to": "до",

    # ----- tweak page -----
    "None": "Нет",
    "Slider": "Слайдер",
    "Text box": "Текстовое поле",
    "Choice list": "Список",
    "String": "Строка",
    "Integer": "Целое",
    "Real": "Дробное",
    "Boolean": "Логическое",
    "\"{text}\" is not a number": "\"{text}\" — не число",
    "\"{text}\" is not true or false": "\"{text}\" — не true и не false",
    "A control adds a slider, text box or list under the switch. Its value replaces every key of the type "
    "Control value in this tweak's writes.":
        "Контрол добавляет под переключатель слайдер, текстовое поле или список. Его значение подставляется "
        "во все ключи этого твика с типом «Значение контрола».",
    "Minimum": "Минимум",
    "Maximum": "Максимум",
    "Step": "Шаг",
    "Default": "По умолчанию",
    "Whole-number limits and step give whole-number values.": "Целые границы и шаг дают целые значения.",
    "Default text": "Текст по умолчанию",
    "Maximum length": "Максимальная длина",
    "Label": "Подпись",
    "Type": "Тип",
    "Value": "Значение",
    "Add Choice": "Добавить вариант",
    "Remove Choice": "Удалить вариант",
    "Choice {n}": "Вариант {n}",
    "Duplicate": "Дублировать",
    "Switch": "Переключатель",
    "hide-dock (presets remember the switch by it)": "hide-dock (по нему пресеты запоминают переключатель)",
    "Shown under the switch. Say what it changes.": "Показывается под переключателем. Опишите, что он меняет.",
    "Id": "Id",
    "On by default": "Включён по умолчанию",
    "Switched on when someone adds the template.": "Включается, когда кто-то добавляет шаблон.",
    "Writes": "Записи",
    "When on": "Когда включён",
    "When off": "Когда выключен",
    "Control": "Контрол",
    "Untitled tweak": "Твик без названия",
    "Written while the switch is on.": "Записывается, пока переключатель включён.",
    "Written while the switch is off, for example to put a key back. Optional.":
        "Записывается, когда переключатель выключен, например чтобы вернуть ключ. Необязательно.",

    # ----- writes -----
    "Plist keys": "Ключи plist",
    "Whole file": "Файл целиком",
    "Empty file": "Пустой файл",
    "mobile (501)": "mobile (501)",
    "root (0)": "root (0)",
    "(no path)": "(нет пути)",
    "no keys": "нет ключей",
    "no file": "нет файла",
    "(empty)": "(пустой)",
    "Write": "Запись",
    "Path on iPhone": "Путь на iPhone",
    "Owner": "Владелец",
    "Choose File…": "Выбрать файл…",
    "Writes an empty file. A path ending in .plist gets an empty plist, since a zero-byte plist can send "
    "iOS 26.2+ into a boot loop.":
        "Записывает пустой файл. По пути с окончанием .plist записывается пустой plist: plist нулевого "
        "размера может отправить iOS 26.2+ в бесконечную перезагрузку.",
    "No file chosen.": "Файл не выбран.",
    "(missing)": "(отсутствует)",
    "Enter where the iPhone stores the file.": "Укажите, где iPhone хранит файл.",
    "GoldenNugget can write here.": "GoldenNugget может записывать сюда.",
    "Choose the file to install": "Выберите файл для установки",
    "File too large": "Файл слишком большой",
    "GoldenNugget accepts files of at most 4 MB.": "GoldenNugget принимает файлы не больше 4 МБ.",
    "Add": "Добавить",
    "Remove": "Удалить",
    "Add a write to say what this tweak changes on the iPhone.":
        "Добавьте запись, чтобы указать, что этот твик меняет на iPhone.",
    "SpringBoard (Home and Lock Screen)": "SpringBoard (экран «Домой» и экран блокировки)",
    "Global preferences (every app)": "Общие настройки (все приложения)",
    "backboardd (display, touches)": "backboardd (экран, касания)",
    "Notes": "Заметки",
    "Pasteboard": "Буфер обмена",
    "App preferences (whole file)": "Настройки приложения (файл целиком)",

    # ----- key table -----
    "Control value": "Значение контрола",
    "Array / Dictionary (JSON)": "Массив / словарь (JSON)",
    "Replaced with the value of the tweak's slider, text box or choice.":
        "Заменяется значением слайдера, текстового поля или списка твика.",
    "Not valid JSON: {error}": "Некорректный JSON: {error}",
    "Use a JSON array [...] or object {...}.": "Используйте JSON-массив [...] или объект {...}.",
    "Key": "Ключ",
    "Add Key": "Добавить ключ",
    "Remove Key": "Удалить ключ",
    "Import from Plist…": "Импорт из plist…",
    "Import from Plist": "Импорт из plist",
    "row {n}: the key is empty and is not saved": "строка {n}: ключ пустой и не сохранится",
    "{key}: the key is used twice; only the last row is saved":
        "{key}: ключ указан дважды, сохранится только последняя строка",
    "row {n}": "строка {n}",
    "Import Keys from a Plist": "Импорт ключей из plist",
    "Property lists (*.plist);;All files (*)": "Файлы plist (*.plist);;Все файлы (*)",
    "The plist has no keys that can be written.": "В plist нет ключей, которые можно записать.",
    "{n} key found.": ("Найден {n} ключ.", "Найдено {n} ключа.", "Найдено {n} ключей."),
    "Tick the ones this write should set.": "Отметьте те, которые должна задать эта запись.",
    "Filter keys": "Фильтр ключей",
    "Select All": "Выбрать все",
    "Select None": "Снять все",
    "Left out ({n}), since config.json cannot hold them: ": "Пропущено ({n}), config.json не может их хранить: ",
    "Import {n} Key": ("Импортировать {n} ключ", "Импортировать {n} ключа", "Импортировать {n} ключей"),
    "Import": "Импортировать",

    # ----- iPhone preview -----
    "Roughly how GoldenNugget lists the template. Try the switches and controls: the right side shows what "
    "GoldenNugget would write. Nothing here changes the template.":
        "Примерно так GoldenNugget показывает шаблон. Попробуйте переключатели и контролы: справа видно, что "
        "GoldenNugget запишет. Здесь ничего в шаблоне не меняется.",
    "What GoldenNugget writes": "Что запишет GoldenNugget",
    "Untitled template": "Шаблон без названия",
    "by {author}": "автор: {author}",
    "No tweaks yet.": "Твиков пока нет.",
    "value {value}": "значение {value}",
    "nothing is written": "ничего не записывается",
    "no writes": "нет записей",
    "owner {owner}": "владелец {owner}",
    "whole file ← {name}": "файл целиком ← {name}",
    "(no file)": "(нет файла)",
    "empty file": "пустой файл",

    # ----- guided tour -----
    "⏸ Pause": "⏸ Пауза",
    "▶ Resume": "▶ Продолжить",
    "Next ▶": "Дальше ▶",
    "End Tour": "Завершить тур",
    "Step {n}": "Шаг {n}",
    "Welcome!": "Добро пожаловать!",
    "This is Batter Builder, the editor for GoldenNugget .batter templates. Watch while it builds a template "
    "with two tweaks. Your own template is put back when the tour ends, and nothing is saved. Pause stops "
    "the tour; Esc or End Tour ends it.":
        "Это Batter Builder, редактор шаблонов .batter для GoldenNugget. Смотрите, как он сам собирает шаблон "
        "с двумя твиками. Когда тур закончится, ваш шаблон вернётся, и ничего не сохранится. «Пауза» "
        "останавливает тур, Esc или «Завершить тур» заканчивают его.",
    "The sidebar": "Боковая панель",
    "Details holds the template's information, Check and Preview runs the checks, and below are the tweaks. "
    "A red number counts the errors left to fix.":
        "В «Сведениях» — данные шаблона, «Проверка и config.json» запускает проверки, а ниже — твики. Красное "
        "число показывает, сколько ошибок осталось исправить.",
    "Template details": "Сведения о шаблоне",
    "The catalog shows these: title, author, description, iOS range and tags.":
        "Это видно в каталоге: название, автор, описание, версии iOS и теги.",
    "Your name or handle.": "Ваше имя или ник.",
    "What the template changes. If it writes files outside Managed Preferences, name them here.":
        "Что меняет шаблон. Если он пишет файлы вне Managed Preferences, перечислите их здесь.",
    "iOS versions": "Версии iOS",
    "The first and last iOS version it works on. Empty means any.":
        "Первая и последняя версия iOS, на которых он работает. Пусто — любая.",
    "Comma-separated words people can find it by in the catalog.":
        "Слова через запятую, по которым шаблон найдут в каталоге.",
    "A tweak is a switch": "Твик — это переключатель",
    "Every tweak shows up in GoldenNugget as a switch. First, its label…":
        "Каждый твик появляется в GoldenNugget как переключатель. Сначала его подпись…",
    "The tweak's internal name. Presets remember the switch by it, so keep it once the template is shared.":
        "Внутреннее имя твика. По нему пресеты запоминают переключатель, так что не меняйте его, когда "
        "шаблон уже опубликован.",
    "Tweak description": "Описание твика",
    "The text under the switch in GoldenNugget.": "Текст под переключателем в GoldenNugget.",
    "Decides whether the switch starts on when someone adds the template.":
        "Определяет, включён ли переключатель сразу, когда кто-то добавляет шаблон.",
    "What to write": "Что записывать",
    "Writes say what the tweak changes on the iPhone. When on holds the writes made while the switch is on.":
        "Записи говорят, что твик меняет на iPhone. «Когда включён» — записи, которые делаются, пока "
        "переключатель включён.",
    "Kind of write": "Вид записи",
    "Plist keys (the usual one), a Whole file stored in the template, or an Empty file.":
        "Ключи plist (обычный случай), файл целиком, хранящийся в шаблоне, или пустой файл.",
    "Path on the iPhone": "Путь на iPhone",
    "The suggestions are the Managed Preferences files GoldenNugget itself uses; their keys merge safely "
    "with GoldenNugget's own.":
        "В подсказках — файлы Managed Preferences, которые использует сам GoldenNugget; их ключи безопасно "
        "объединяются с ключами GoldenNugget.",
    "Green means OK": "Зелёный — всё в порядке",
    "GoldenNugget can write to this path. A wrong path turns this note red.":
        "GoldenNugget может записывать по этому пути. При неверном пути надпись станет красной.",
    "Like this one": "Вот так",
    "Outside /var/: red error. Let's put the right path back.":
        "Вне /var/ — красная ошибка. Вернём правильный путь.",
    "Key and value": "Ключ и значение",
    "Add Key, then the key's name. SBDisableParallax turns the icon parallax off.":
        "«Добавить ключ», затем имя ключа. SBDisableParallax выключает параллакс иконок.",
    "Value type": "Тип значения",
    "Boolean true turns it on. Other types: numbers, text, arrays, or Control value.":
        "Логическое true включает его. Другие типы: числа, текст, массивы или значение контрола.",
    "What to write when the switch is turned off. Here: set the key back to false.":
        "Что записать, когда переключатель выключают. Здесь — вернуть ключу значение false.",
    "false": "false",
    "Untick it and the value becomes false.": "Снимите галочку, и значение станет false.",
    "A second tweak": "Второй твик",
    "Now a tweak with a slider. Add Tweak is at the bottom left.":
        "Теперь твик со слайдером. «Добавить твик» — внизу слева.",
    "The red number": "Красное число",
    "The new tweak has an error for now: its write has no key yet. The number goes away once it is fixed.":
        "В новом твике пока ошибка: в его записи ещё нет ключа. Число исчезнет, когда она будет исправлена.",
    "The Lock Screen's auto-lock.": "Автоблокировка экрана блокировки.",
    "The key": "Ключ",
    "SBMinimumLockscreenIdleTime: after how many minutes the Lock Screen turns the display off.":
        "SBMinimumLockscreenIdleTime: через сколько минут экран блокировки выключает дисплей.",
    "With the type Control value, the value comes from the slider.":
        "С типом «Значение контрола» значение берётся из слайдера.",
    "The control": "Контрол",
    "Choose what appears under the switch: a slider, a text box or a choice list.":
        "Выберите, что появится под переключателем: слайдер, текстовое поле или список.",
    "The slider's smallest value.": "Наименьшее значение слайдера.",
    "Its largest value.": "Наибольшее значение.",
    "How far it moves. Whole numbers give whole-number values.":
        "На сколько он сдвигается. Целые числа дают целые значения.",
    "Where the slider starts.": "С какого значения начинается слайдер.",
    "No errors left": "Ошибок не осталось",
    "The red number is gone.": "Красное число исчезло.",
    "The same rules GoldenNugget applies when it loads a template. Ready means it is good to go.":
        "Те же правила, что GoldenNugget применяет при загрузке шаблона. «Готово» значит, что всё в порядке.",
    "Risk notes": "Оценки риска",
    "Every write gets a risk level. Keys in Managed Preferences are low risk.":
        "У каждой записи есть уровень риска. Ключи в Managed Preferences — низкий риск.",
    "config.json": "config.json",
    "Exactly what is saved in the file. No JSON by hand.": "Ровно то, что сохранится в файле. Без ручного JSON.",
    "Save writes the .batter file. (The tour does not save anything.)":
        "«Сохранить» записывает файл .batter. (Тур ничего не сохраняет.)",
    "Checks the template, saves it as <id>.batter and opens GitHub: drag the file in and click Propose "
    "changes. The team reviews it before it appears in GoldenNugget's Community Catalog.":
        "Проверяет шаблон, сохраняет его как <id>.batter и открывает GitHub: перетащите файл и нажмите "
        "Propose changes. Команда проверит шаблон, прежде чем он появится в каталоге сообщества GoldenNugget.",
    "That's it!": "Вот и всё!",
    "When the tour ends your own template comes back. Click End Tour now, or wait a moment.":
        "Когда тур закончится, ваш шаблон вернётся. Нажмите «Завершить тур» сейчас или подождите немного.",
}
