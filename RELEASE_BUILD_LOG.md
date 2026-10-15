# ⏱️ Отчёт о завершении сборки LightLauncher v0.52

- **Версия релиза:** `v0.52`
- **Дата и время завершения работы:** `2026-10-16 00:13:45` (UTC+5)
- **Компилятор Nuitka:** `v4.1.2` (CPython 3.11.9, GCC 15.2.0)
- **Флаги компиляции:**
  - `--standalone`
  - `--windows-disable-console`
  - `--windows-icon-from-ico=mclovin.ico`
  - `--output-filename=LightLauncher.exe`
  - `--enable-plugin=pyqt6`
  - `--noinclude-qt-translations`
  - `--noinclude-dlls` (исключены `*Qt6Pdf*.dll`, `*Qt6Network*.dll`, `*Qt6Svg*.dll`, лишние декодеры изображений, tls и offscreen плагины)
  - `--lto=auto`
  - Сжатие UPX: **отключено** (сжатие выполняется через Inno Setup)
- **Инсталлятор Inno Setup:**
  - Файл: `installer_output\LightLauncher-setup-v0.52.exe`
  - Размер: ~32.6 МБ (включает все 8 HD фонов, runtime и зависимости)
  - Сжатие: `lzma2/ultra64`
- **Git:** Все файлы закоммичены отдельными коммитами в ветку `main`.
