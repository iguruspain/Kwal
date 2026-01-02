# KWAL - Copilot Instructions

## 1. Calidad y Limpieza de Código
- **Prohibido el Código Muerto:** Elimina funciones, variables o bloques obsoletos inmediatamente. No dejes código comentado.
- **Comentarios Relevantes:** Solo lógica compleja o decisiones técnicas. Documentación en **INGLÉS**. Nada de comentarios que reemplacen a funcionalidad eliminada o placeholders.
- **Sin Omisiones:** Proporciona siempre el código completo. Prohibido usar `// ... rest of code ...`.
- **Consistencia:** Actualiza todas las referencias al refactorizar o renombrar.

## 2. Python y Pylance (Strict Mode)
- **Compatibilidad:** Python 3.10+ con Type Hinting obligatorio.
- **Zero Warnings:** Compatible con `typeCheckingMode: "strict"`.
  - Prohibido el uso de `Any`. Maneja `Optional` y `None` explícitamente.
  - Usa `@Slot()` y `@Property()` de `PySide6.QtCore` con firmas de tipo completas.
- **Manejo de Errores:** Usa `logging` en lugar de `print`. Captura excepciones en los slots de Qt.

## 3. QML y UI (Kirigami)
- **Sintaxis:** Revisión estricta de jerarquía y cierre de llaves.
- **Modularización:** Divide la UI en componentes lógicos, `main.qml` es el archivo principal. Los componentes nuevos deben ir en `src/qml/` (ej: `CustomComponent.qml`).
- **Orden de Propiedades:** `id` > layout > visuales > señales/funciones.
- **Rendimiento:** Evita bindings circulares y usa `Connections` para señales de Python.

## 4. Arquitectura y Estructura (Basado en `src/`)
El agente debe respetar rigurosamente la estructura del proyecto:
- **`src/controllers/`:** Lógica de control y puente entre Python y QML (`controller.py`).
- **`src/models/`:** Definición de datos y lógica de negocio (`models.py`).
- **`src/qml/`:** Archivos de interfaz de usuario (`main.qml`).
- **`src/app.py` & `src/__main__.py`:** Puntos de entrada y configuración de la aplicación.
- **Reutilización:** Antes de crear lógica nueva, revisa si existe funcionalidad aprovechable en los módulos actuales de `src/`.

## 5. Comportamiento del Agente
- **Transparencia:** Explica cambios arquitectónicos no solicitados y pide confirmación.
- **Enfoque:** No agregues funcionalidades "extra" fuera del scope del usuario.
- **Commits:** Usa **Conventional Commits** para sugerencias de mensajes. No realices commits automáticos.
- **Idioma:** Código, variables y documentación técnica estrictamente en **INGLÉS**.

## 6. Tecnologías y Referencias
- **Stack:** Python (PySide6) + QML (Kirigami) para KDE Plasma.
- **Libreria** Usa exclusivamente `PySide6`. Prohibido el uso de `PyQt6`.
- **Documentación:** Seguir estándares de [Qt](https://doc.qt.io), [KDE Develop](https://develop.kde.org) y[Kirigami](https://develop.kde.org/docs/getting-started/kirigami/).

## 7. Rigor técnico
- **Integridad Técnica:** No realices `fallbacks` a conveniencia. Si el código no pasa el análisis de Pylance o hay un conflicto de tipos entre Python y QML, o alguna funcionalidad no está implementada correctamente, no uses atajos que degraden la calidad del código (como tipado dinámico o supresión de advertencias).
- **Logging y Depuración:** Implementa un sistema de logging robusto para todas las interacciones entre Python y QML. Evita el uso de `print` para depuración. Utiliza niveles de logging adecuados (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`). Utiliza e implementa el logging para rastrear errores y eventos importantes en la aplicación, de esta manera se facilita el mantenimiento y la resolución de problemas.
- **Prioridad de Arreglos:** Prioriza la corrección de errores y advertencias antes de agregar nuevas funcionalidades o realizar refactorizaciones. Si una implementación sugerida falla, el siguiente paso debe ser corregirla bajo los mismos estándares de calidad originales, no simplificarla eliminando las restricciones de seguridad.
- **Ignora** ignora los warnings de `QML ToolTip: Binding loop detected for property 'contentWidth'`