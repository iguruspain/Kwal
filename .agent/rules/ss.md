---
trigger: always_on
---

# KWAL - Copilot Instructions

## 1. Calidad y Limpieza de Código
- **Prohibido el Código Muerto:** Elimina funciones, variables, comentarios o bloques obsoletos inmediatamente. No dejes código comentado que sea considerado como código muerto o referente a funcionalidades eliminadas o erróneas.
- **Comentarios Relevantes:** Solo lógica compleja o decisiones técnicas. Documentación en **INGLÉS**. Nada de comentarios que reemplacen a funcionalidad eliminada o placeholders.
- **Sin Omisiones:** Proporciona siempre el código completo. Prohibido usar `// ... rest of code ...`.
- **Consistencia:** Actualiza todas las referencias al refactorizar o renombrar.

## 2. Arquitectura y Estructura (Basado en `src/`)
El agente debe respetar rigurosamente la estructura del proyecto:
- **`src/controllers/`:** Lógica de control y puente entre Python y QML (`controller.py`).
- **`src/models/`:** Definición de datos y lógica de negocio (`models.py`).
- **`src/qml/`:** Archivos de interfaz de usuario (`main.qml`).
- **`src/utils/`:** Funciones auxiliares y utilidades (ejemplo: `color_utils.py`).
- **`src/resources/`:** Recursos estáticos como imágenes y otros archivos.
- **`src/app.py` & `src/__main__.py`:** Puntos de entrada y configuración de la aplicación.
- **Reutilización:** Antes de crear lógica nueva, revisa si existe funcionalidad aprovechable en los módulos actuales de `src/`.

## 3. Python y Pylance (Strict Mode)
- **Compatibilidad:** Python 3.10+ con Type Hinting obligatorio.
- **Zero Warnings:** Compatible con `typeCheckingMode: "strict"`.
  - Prohibido el uso de `Any`. Maneja `Optional` y `None` explícitamente.
  - Usa `@Slot()` y `@Property()` de `PySide6.QtCore` con firmas de tipo completas.
- **Manejo de Errores:** Usa `logging` en lugar de `print`. Captura excepciones en los slots de Qt.

## 4. Seguridad y Portabilidad (Security & Portability)
- **Rutas Prohibidas:** Estrictamente prohibido usar rutas absolutas hardcoded como `/home/usuario` o `~`.
  - Usa `Path.home()` para el directorio de usuario.
  - Usa `os.environ.get("XDG_CONFIG_HOME")` para configuraciones.
  - Usa `QStandardPaths` de PySide6 para rutas estándar del sistema.
- **Inyección de Comandos:**
  - Al usar `subprocess`, pasa los argumentos como una lista (`["cmd", "arg"]`), nunca como un string completo con `shell=False`.
  - Si debes generar scripts dinámicos (ej: JavaScript para `qdbus`), **sanitiza/escapa** cualquier variable insertada (especialmente rutas de archivo que pueden contener comillas o caracteres especiales).
- **Validación de Archivos:** Verifica siempre `exist()` y `is_file()` antes de intentar leer o procesar rutas proporcionadas por el usuario.

## 5. Gestión de estados (State Management) entre Python y QML
- **Fuente única de información:** El controlador de Python almacena el estado de la aplicación. QML se usa exclusivamente para presentación.
- **Persistencia:** Las propiedades volátiles de QML (p. ej., entradas de texto, valores de los controles deslizantes, selecciones actuales) se pierden al destruir la vista (p. ej., al cambiar de pestaña). Transfiera este estado a las propiedades del controlador de Python (variables "Draft") para garantizar la persistencia. **Nunca confíes en que una propiedad QML mantendrá su valor si el usuario cambia de vista (Tab/Page).**
- **Sincronización:** Utilice señales y enlaces de propiedades para mantener la sincronización inmediata entre QML y Python. No confíe en el estado interno de QML para los datos importantes.

## 6. Experiencia de Usuario y Manejo de Errores Visual (UX Error Handling)
- **Filosofía "Pasiva por Defecto":**
  - **Éxito/Info:** No interrumpas al usuario. Usa cambios de estado sutiles o logs internos.
  - **Errores:** Usa **Notificaciones Pasivas** (Kirigami Overlay/Toast) que desaparecen solas.
  - **Crítico:** Solo usa Diálogos Modales (Popups con botón "Aceptar") si la aplicación no puede continuar o hay riesgo inminente de pérdida de datos.
- **Canal de Notificación:** Usa la señal `notification(message, type)` del controlador para enviar errores al frontend. No imprimas errores directamente en la consola (`print`) si el usuario necesita saberlo.
- **Mensajes Claros:** Los mensajes de error al usuario deben explicar *qué pasó* en lenguaje natural, no mostrar trazas de error de Python (ej: "No se pudo guardar la imagen" vs "IOError: Broken pipe").

## 7. QML y UI (Kirigami)
- **Sintaxis:** Revisión estricta de jerarquía y cierre de llaves.
- **Modularización:** Divide la UI en componentes lógicos, `main.qml` es el archivo principal. Los componentes nuevos deben ir en `src/qml/` (ej: `CustomComponent.qml`). Pregunta al usuario antes de crear nuevos componentes.
- **Orden de Propiedades:** `id` > layout > visuales > señales/funciones.
- **Rendimiento:** Evita bindings circulares y usa `Connections` para señales de Python.
- **Autocompletado y codigo:** Los módulos QML están en /usr/lib/qt6/qml. Cuando sugieras código QML, asegúrate de usar la sintaxis moderna de Qt 6 (sin versiones en los imports, ej: import QtQuick en lugar de import QtQuick 2.15). Los componentes que uso principalmente son de QtQuick, QtQuick.Controls y QtQuick.Layouts.

## 8. Rigor técnico
- **Integridad Técnica:** No realices `fallbacks` a conveniencia. Si el código no pasa el análisis de Pylance o hay un conflicto de tipos entre Python y QML, o alguna funcionalidad no está implementada correctamente, no uses atajos que degraden la calidad del código (como tipado dinámico o supresión de advertencias).
- **Logging y Depuración:** Implementa un sistema de logging robusto para todas las interacciones entre Python y QML. Evita el uso de `print` para depuración. Utiliza niveles de logging adecuados (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`). Utiliza e implementa el logging para rastrear errores y eventos importantes en la aplicación, de esta manera se facilita el mantenimiento y la resolución de problemas.
- **Prioridad de Arreglos:** Prioriza la corrección de errores y advertencias antes de agregar nuevas funcionalidades o realizar refactorizaciones. Si una implementación sugerida falla, el siguiente paso debe ser corregirla bajo los mismos estándares de calidad originales, no simplificarla eliminando las restricciones de seguridad.
- **Ignora** ignora los warnings de `QML ToolTip: Binding loop detected for property 'contentWidth'`

## 9. Comportamiento del Agente
- **Transparencia:** Explica cambios arquitectónicos no solicitados y pide confirmación.
- **Enfoque:** No agregues funcionalidades "extra" fuera del scope del usuario.
- **Commits:** Usa **Conventional Commits** para sugerencias de mensajes. No realices commits automáticos.
- **Idioma:** Aplicación, código, variables y documentación técnica estrictamente en **INGLÉS**.

## 10. Tecnologías y Referencias
- **Stack:** Python (PySide6) + QML (Kirigami) para KDE Plasma.
- **Libreria** Usa exclusivamente `PySide6`. Prohibido el uso de `PyQt6`.
- **Documentación:** Seguir estándares de [Qt](https://doc.qt.io), [KDE Develop](https://develop.kde.org) y [Kirigami](https://develop.kde.org/docs/getting-started/kirigami/).

## 11. Recuerda
- El usuario confía en ti para mantener la calidad y coherencia del proyecto.
- No asumas acciones sobre la intención del usuario sin confirmación.
- El usuario es novato en desarrollo de software; explica claramente cualquier cambio complejo.
- Siempre pregunta si tienes dudas sobre los requisitos o el alcance antes de proceder.