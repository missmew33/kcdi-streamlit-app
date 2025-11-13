# kcdi-streamlit-app

Aplicación web para el análisis de los índices **KCDI** y **KRATOS** (Justicia Epistémica) a partir de datos de Scopus. Desarrollada con Python y Streamlit.

## Descripción

Esta es una aplicación web interactiva desarrollada con **Python** y **Streamlit** para analizar el **Índice de Diversidad de Contribución al Conocimiento (KCDI)** y su indicador complementario **KRATOS**. Permite a los usuarios subir un archivo de Scopus (.csv o .xlsx) y visualizar métricas de justicia epistémica, analizando la diversidad de género, región, colaboración e impacto en las contribuciones.

## Características

- **Análisis KCDI configurable**: Calcula el índice KCDI, el Índice de Shannon y el factor de ponderación a partir de pesos ajustables para género y región.
- **Indicador KRATOS**: Resume tres dimensiones (representación, colaboración e impacto) a partir de los datos disponibles en el archivo.
- **Visualizaciones**: Genera una brújula KCDI, gráficos interseccionales, distribuciones por región/género y una tendencia temporal (si la columna `Year` está disponible).
- **Procesamiento de Datos**: Limpia y preprocesa los datos de Scopus, infiriendo género y clasificación regional (Norte/Sur Global) a partir de los datos de los autores.
- **Descarga y transparencia**: Permite descargar el conjunto de datos procesado y revisar la tabla de pesos aplicada y la metodología KRATOS desde la propia interfaz.

## Cómo Usar

1. Sube un archivo `.csv` o `.xlsx` desde tu sistema.
2. El archivo debe contener las columnas **`Authors`** y **`Country`**; si incluye `Year` y `Cited by`, se habilitan gráficos adicionales y el componente de impacto del KRATOS.
3. Ajusta los pesos en la barra lateral para reflejar tus criterios de justicia epistémica.
4. La aplicación procesará los datos automáticamente y mostrará los resultados.

## Despliegue

Esta aplicación puede desplegarse en [Streamlit Community Cloud](https://streamlit.io/cloud) o en cualquier entorno compatible con Streamlit.

## Dependencias

Las dependencias necesarias se especifican en el archivo `requirements.txt`.
