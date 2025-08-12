# kcdi-streamlit-app
Aplicación web para el análisis del Índice KCDI (Justicia Epistémica) a partir de datos de Scopus. Desarrollada con Python y Streamlit
# Aplicación KCDI para Análisis de Justicia Epistémica

## Descripción
Esta es una aplicación web interactiva desarrollada con **Python** y **Streamlit** para analizar el **Índice de Diversidad de Contribución al Conocimiento (KCDI)**. Permite a los usuarios subir un archivo de Scopus (.csv o .xlsx) y visualizar métricas de justicia epistémica, analizando la diversidad de género y región en las contribuciones.

## Características
-   **Análisis KCDI**: Calcula el índice KCDI, el Índice de Shannon y el factor de ponderación.
-   **Visualizaciones**: Genera un gráfico de brújula KCDI y un gráfico de barras interseccional.
-   **Procesamiento de Datos**: Limpia y preprocesa los datos de Scopus, infiriendo género y clasificación regional (Norte/Sur Global) a partir de los datos de los autores.
-   **Descarga de Datos**: Permite descargar el conjunto de datos procesado para análisis posteriores.

## Cómo Usar
1.  Sube un archivo `.csv` o `.xlsx` desde tu sistema.
2.  El archivo debe contener las columnas **`Authors`** y **`Country`**.
3.  La aplicación procesará los datos automáticamente y mostrará los resultados.

## Despliegue
Esta aplicación está desplegada en [Streamlit Community Cloud](https://streamlit.io/cloud).

## Dependencias
Las dependencias necesarias se especifican en el archivo `requirements.txt`.
