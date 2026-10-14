"""UI модуль LightLauncher — поддержка стилей Modern и Classic."""

from design_classic import Ui_MainWindowClassic
from design_modern import Ui_MainWindowModern

# По умолчанию используется современный Glassmorphism дизайн
Ui_MainWindow = Ui_MainWindowModern

__all__ = ["Ui_MainWindow", "Ui_MainWindowClassic", "Ui_MainWindowModern"]
