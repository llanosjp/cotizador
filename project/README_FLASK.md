# Plataforma de Verificación DNI

## Instalación y Ejecución

### 1. Instalar Dependencias de Python

```bash
pip install -r requirements.txt
```

### 2. Ejecutar el Servidor Flask

```bash
python app.py
```

El servidor estará disponible en: `http://localhost:5000`

## Características

### Módulo 1: Consulta Masiva
- Carga de archivos Excel (.xls, .xlsx)
- Validación automática de columna "DNI"
- Barra de progreso en tiempo real
- Visualización de resultados con indicadores visuales
- Exportación a Excel consolidado

### Módulo 2: Búsqueda Individual
- Consulta rápida de DNI
- Tarjetas de estado visuales (APROBADO/RECHAZADO)
- Feedback instantáneo

## Estructura de Archivos

```
project/
├── app.py                 # Backend Flask
├── requirements.txt       # Dependencias Python
├── templates/
│   ├── upload.html       # Página de carga masiva
│   ├── resultados.html   # Página de resultados
│   └── buscar.html       # Página de búsqueda individual
├── uploads/              # Archivos subidos (creado automáticamente)
└── results/              # Archivos de resultados (creado automáticamente)
```

## Formato del Archivo Excel

El archivo debe contener una columna llamada **"DNI"** con los números de documento a verificar.

Ejemplo:
| DNI      |
|----------|
| 12345678 |
| 87654321 |
| 11223344 |
