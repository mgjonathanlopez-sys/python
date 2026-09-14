# Gestor de Proyectos de Investigación

Aplicación de escritorio configurable para administrar proyectos de investigación y proyectos financiados. Funciona de manera local con Python, PySide6, SQLite y SQLAlchemy.

## Funciones incluidas

- Dashboard con cumplimiento, vencimientos, próximas actividades, evidencias y organizaciones.
- Proyectos y configuración general.
- Plan de trabajo con actividades, responsables, fechas, estados, prioridades, dependencias y avance.
- Cronograma tipo Gantt por meses.
- Evidencias vinculadas a cada actividad.
- Gestión documental, revisión sistemática, instrumentos, trabajo de campo y análisis.
- Taller participativo, AHP, indicadores, productos, informes, alertas y auditoría.
- Informes HTML, exportación CSV y respaldo ZIP.

Regla de cumplimiento: actividad terminada + evidencia requerida = cumplimiento acreditado.

## Instalar en Windows 10 u 11

1. Pulse Code > Download ZIP.
2. Descomprima el ZIP en una carpeta permanente.
3. Instale Python 3.11 o superior desde https://www.python.org/downloads/windows/
4. Active Add Python to PATH durante la instalación.
5. Haga doble clic en Instalar_Gestor.bat.
6. Abra la aplicación con el acceso directo creado en el escritorio.

## Crear un EXE portátil

Ejecute Crear_EXE.bat. El resultado se genera en dist\\Gestor_Proyectos_Investigacion.exe y puede copiarse a otro equipo Windows.

## Privacidad y configuración

La versión pública no contiene información real de ningún proyecto. En el primer inicio se registran localmente el código, nombre, territorio, investigador y fechas. Los datos no se envían a internet.

Use plantilla_actividades.csv y plantilla_organizaciones.csv para importaciones masivas. Las fechas deben usar AAAA-MM-DD.

## Datos locales

En Windows se guardan en %LOCALAPPDATA%\\ResearchProjectManager:

- gestor_proyectos.sqlite
- evidencias
- documentos
- reportes
- respaldos

Estos elementos se excluyen del repositorio público.
