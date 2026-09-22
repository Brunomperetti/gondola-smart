# Gondola Smart

**Gondola Smart MVP v0.1** es el núcleo de una aplicación que compara productos de
supermercado de distintos tamaños y presentaciones. Convierte cada precio a una
unidad adecuada para su categoría (por ejemplo, ARS/100 g, ARS/kg, ARS/litro,
ARS/unidad o ARS/metro) y ordena las alternativas desde la más conveniente.

## Flujo del producto

El flujo previsto es:

```text
Foto de góndola
       ↓
Detección de productos
       ↓
Extracción de precios y cantidades
       ↓
Normalización
       ↓
Ranking
       ↓
Mejor compra
```

La versión 0.1 comienza en datos estructurados. Incluye un detector mock que lee
productos ficticios de `examples/products.json`; todavía no realiza OCR ni analiza
imágenes. El detector está aislado del motor de comparación para poder sustituirlo
en el futuro sin modificar la lógica de negocio.

## Arquitectura

```text
app/
├── api/routes.py              # Contratos y endpoints HTTP
├── comparison/
│   ├── categories.py          # Reglas centrales por categoría
│   ├── normalize.py           # Conversiones y precios normalizados
│   └── ranking.py             # Agrupación y ranking
├── models/product.py          # Modelo y validaciones del producto
├── vision/mock_detector.py    # Proveedor mock reemplazable
└── main.py                    # Aplicación FastAPI
examples/products.json         # Datos de demostración
tests/                         # Pruebas unitarias y de API
```

El motor dentro de `app/comparison` no depende de FastAPI. Las categorías
soportadas son `cookies`, `toothpaste`, `pasta`, `rice`, `shampoo`, `detergent`,
`soda`, `toilet_paper`, `paper_towel`, `diapers` y `eggs`. Los productos se
comparan únicamente dentro de su categoría.

Para papeles, el total de metros se obtiene mediante
`package_count × unit_length`. Un producto con `confidence < 0.75` se conserva en
el ranking y aparece con `requires_confirmation: true`.

## Instalación

Se requiere Python 3.12.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Ejecución

Iniciar el servidor de desarrollo:

```bash
uvicorn app.main:app --reload
```

La documentación interactiva Swagger queda disponible en
<http://127.0.0.1:8000/docs>.

### Endpoints

- `GET /health`: estado y versión de la aplicación.
- `POST /compare`: recibe `{"products": [...]}` y agrupa/rankea esos productos.
- `GET /demo`: compara los productos ficticios del archivo de ejemplo.
- `POST /analyze/mock`: simula detección, normalización y ranking completos.

Ejemplo mínimo para `/compare`:

```bash
curl -X POST http://127.0.0.1:8000/compare \
  -H 'Content-Type: application/json' \
  -d '{"products":[{"id":"rice_1","name":"Arroz","brand":"Ejemplo","category":"rice","price":1800,"quantity":1,"unit":"kg"}]}'
```

## Pruebas

Con el entorno virtual activo:

```bash
pytest
```

Las pruebas cubren conversiones, todas las modalidades de normalización,
validaciones, ranking, agrupación por categoría, confianza y los endpoints.

## Alcance futuro

Una v0.2 puede introducir una interfaz formal de detectores, un primer proveedor
de visión/OCR, revisión manual de detecciones inciertas y más reglas de
presentación (por ejemplo, papel de cocina comparable por hoja). No forman parte
de esta versión el reconocimiento real de imágenes, autenticación, una base de
datos ni una aplicación móvil.
