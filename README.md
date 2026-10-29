# ZB_2Blender

**Управление как в ZBrush в Sculpt Mode Blender: навигация, маска и видимость жестами Ctrl и Ctrl+Shift, клавиши ZBrush, кисть Move, гизмо, сабтулы и DynaMesh.**

[![Latest release](https://img.shields.io/github/v/release/Ddosena/ZB_2Blender?label=version)](https://github.com/Ddosena/ZB_2Blender/releases/latest)
[![License](https://img.shields.io/badge/license-GPL--3.0--or--later-blue)](LICENSE)

**[Скачать Bl_2_zbr_sclpt.py](https://github.com/Ddosena/ZB_2Blender/releases/latest/download/Bl_2_zbr_sclpt.py)** · **[Установка](docs/INSTALL_RU.md)** · **[Как пользоваться](docs/USAGE_RU.md)** · **[Решение проблем](docs/FAQ_RU.md)**

Бесплатный аддон для тех, кто пришёл в Blender из ZBrush или учится скульптингу по его логике. Это один файл `.py`: Python и другие программы ставить не нужно, аккаунт GitHub для скачивания не нужен. Аддон меняет только Sculpt Mode. Кнопка **ZB** в шапке сразу возвращает обычный Blender.

![Sculpt Mode с аддоном: кнопка ZB в шапке, плитка кисти, панель N → ZBrush](docs/images/sculpt_zb.png)

## Что нужно

**Blender 5.2.** Аддон проверен на 5.2.2 и 5.2.3. Более старые версии не поддерживаются.

## Установка за минуту

1. Скачайте [Bl_2_zbr_sclpt.py](https://github.com/Ddosena/ZB_2Blender/releases/latest/download/Bl_2_zbr_sclpt.py). Открывать и распаковывать файл не нужно.
2. В Blender откройте **Edit → Preferences → Add-ons**. Справа вверху нажмите стрелку **⌄** → **Install from Disk…** и выберите скачанный файл.
3. Проверьте, что у **Bl_2_zbr_sclpt** стоит галочка. Перейдите в **Sculpt Mode**: в начале шапки инструментов появится кнопка **ZB**.

Подробная инструкция с проверкой, обновлением и удалением — в [docs/INSTALL_RU.md](docs/INSTALL_RU.md).

## Что умеет

| Функция | Как работает |
| --- | --- |
| **Навигация** | Колесо мыши (СКМ) или кнопка пера вращает вид. <kbd>Shift</kbd> во время вращения прилипает к углам 90°, как в ZBrush. По желанию можно вращать ЛКМ по пустому месту, как в ZBrush. |
| **Маска (Ctrl)** | <kbd>Ctrl</kbd>+протяжка по мешу рисует маску кистью, с пустого места — рамкой. <kbd>Ctrl</kbd>+клик размывает маску, клик по фону её инвертирует, <kbd>Alt</kbd> стирает. |
| **Видимость и обрезка (Ctrl+Shift)** | <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+протяжка — Trim Lasso или другой выбранный инструмент. Клик по полигруппе изолирует её, клик по фону показывает всё. |
| **DynaMesh** | Пустая <kbd>Ctrl</kbd>-рамка по фону делает ремеш. Если есть маска, первая такая рамка снимает маску, а вторая делает ремеш. Плотность — поле **Res** в шапке, размер вокселя — <kbd>Ctrl</kbd>+<kbd>R</kbd>. |
| **Move (Grab, клавиша 3)** | Тянет сферу вокруг точки нажатия и цепляет меш, даже если перо чуть мимо. С BackfaceMask двигается сторона, которая смотрит туда, куда тянете. |
| **Клавиши ZBrush** | Пробел — размер кисти, <kbd>U</kbd> — сила, <kbd>O</kbd> — жёсткость, <kbd>L</kbd> — Lazy Mouse, <kbd>X</kbd> — симметрия, <kbd>B</kbd> — кисти, <kbd>Q</kbd> — кисть, <kbd>W</kbd> / <kbd>E</kbd> — гизмо, <kbd>D</kbd> / <kbd>Shift</kbd>+<kbd>D</kbd> — уровни Multires, <kbd>1</kbd>–<kbd>4</kbd> — кисти. |
| **Гизмо (W / E)** | Встаёт в центр незамаскированной части. <kbd>Alt</kbd> двигает гизмо без меша и ставит его по поверхности. <kbd>Ctrl</kbd>+протяжка стрелки копирует или выдавливает незамаскированное. |
| **G / R / S** | Перемещение, поворот и масштаб незамаскированной части вокруг центра гизмо, <kbd>X</kbd> <kbd>Y</kbd> <kbd>Z</kbd> — по осям гизмо. |
| **Сабтулы** | <kbd>Shift</kbd>+<kbd>A</kbd> добавляет примитив отдельным объектом, отделяет замаскированное или объединяет с нижним мешем (Merge Down). Двойной <kbd>Alt</kbd>+клик переходит на другой объект. |
| **Полигруппы** | Пирог <kbd>Alt</kbd>+<kbd>W</kbd>, <kbd>Ctrl</kbd>+<kbd>W</kbd> — полигруппа из маски. |
| **Примитив вместо меша** | Иконка ⚙ над гизмо заменяет незамаскированную часть сферой, кубом, цилиндром и другими примитивами. |
| **Отмена** | <kbd>Ctrl</kbd>+<kbd>Z</kbd> / <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>Z</kbd> в Sculpt не выводят в Object Mode. Действия аддона отменяются одним нажатием. |
| **Кисти** | Копии кистей Essentials с Size Pressure, крупная плитка текущей кисти внизу слева. |

Все жесты, клавиши и иллюстрации — в [docs/USAGE_RU.md](docs/USAGE_RU.md).

## Если что-то пошло не так

Нажмите кнопку **ZB** или <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>Alt</kbd>+<kbd>Z</kbd>: вернётся обычный Blender. Частые вопросы разобраны в [docs/FAQ_RU.md](docs/FAQ_RU.md). Об ошибке можно написать в [Issues](https://github.com/Ddosena/ZB_2Blender/issues): укажите версии Blender и аддона и опишите, что вы делали.

## История версий

[CHANGELOG.md](CHANGELOG.md)

## Лицензия

[GPL-3.0-or-later](LICENSE). Аддон можно свободно использовать, изменять и распространять на условиях этой лицензии.
