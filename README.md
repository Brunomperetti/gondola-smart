# Gondola Smart

## Gondola Smart MVP v0.2 — Real Shelf Vision

Gondola Smart recibe de una a tres fotografías reales de una góndola, extrae
productos y etiquetas de precio con un proveedor de visión y entrega solamente
los productos seguros al motor matemático de comparación de v0.1. Los resultados
inciertos siguen visibles, pero nunca pueden convertirse silenciosamente en la
«mejor compra».

```text
imágenes → validación → proveedor de visión → candidatos incompletos
         → validación determinística → deduplicación → Product v0.1 → ranking
```

La IA **solo observa y extrae** nombre, marca, variante, categoría, precio,
cantidad, presentación, confianza y ubicaciones aproximadas. No calcula precios
normalizados ni elige ganadores. La validación, exclusión de datos dudosos,
normalización y clasificación son código determinístico.

## Arquitectura

```text
app/
├── api/routes.py                 # HTTP y traducción de errores
├── comparison/                   # motor determinístico estable de v0.1
├── models/
│   ├── product.py                # producto estricto y comparable
│   └── detection.py              # candidato visual nullable, issues y bbox
├── services/analysis.py          # orquestación del pipeline
├── vision/
│   ├── base.py                   # protocolo neutral y errores
│   ├── prompts.py                # prompt conservador y testeable
│   ├── openai_provider.py        # OpenAI Responses API
│   ├── mock_detector.py          # proveedor local/CI
│   ├── provider_factory.py       # selección por configuración
│   └── deduplication.py          # solapamiento entre fotos
├── config.py                     # variables de entorno
└── main.py
```

Las categorías comparables son `cookies`, `toothpaste`, `pasta`, `rice`,
`shampoo`, `detergent`, `soda`, `toilet_paper`, `paper_towel`, `diapers` y
`eggs`. Una categoría desconocida se conserva en `unsupported_products` con el
issue `UNSUPPORTED_CATEGORY`, sin entrar al ranking.

## Instalación y configuración

Se requiere Python 3.12.

```bash
python3.12 -m venv .venv
source .venv/bin/activate                 # Windows: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
cp .env.example .env
```

La aplicación lee variables del entorno (un archivo `.env` puede cargarse desde
la shell o con la herramienta preferida; no se versiona):

```dotenv
VISION_PROVIDER=mock
OPENAI_API_KEY=
OPENAI_VISION_MODEL=gpt-5.6-luna
OPENAI_TIMEOUT_SECONDS=45
MAX_IMAGES_PER_ANALYSIS=3
MAX_IMAGE_SIZE_MB=10
```

Para visión real, exportar `VISION_PROVIDER=openai` y `OPENAI_API_KEY` con una
clave válida. El modelo es configurable con `OPENAI_VISION_MODEL`; ninguna clave
se incluye en código, respuestas o logs. Para desarrollo y CI, `mock` no consume
la API.

> La aplicación no carga `.env` por sí sola. En Bash puede usarse
> `set -a; source .env; set +a`; PowerShell puede definir cada variable con
> `$env:VARIABLE="valor"`.

## Ejecución y endpoints

```bash
uvicorn app.main:app --reload
```

Swagger queda en <http://127.0.0.1:8000/docs>.

- `GET /health`: salud y versión.
- `POST /compare`: conserva el contrato estructurado de v0.1.
- `GET /demo` y `POST /analyze/mock`: demostración compatible con v0.1.
- `POST /analyze`: `multipart/form-data`, campo repetible `files` (1–3 JPEG,
  PNG o WebP), más `category_hint` y `query` opcionales.

Prueba real con una o varias fotos:

```bash
curl -X POST http://127.0.0.1:8000/analyze \
  -F 'files=@gondola-izquierda.jpg;type=image/jpeg' \
  -F 'files=@gondola-derecha.jpg;type=image/jpeg' \
  -F 'category_hint=toothpaste' \
  -F 'query=pasta dental menta'
```

En PowerShell:

```powershell
curl.exe -X POST http://127.0.0.1:8000/analyze `
  -F "files=@gondola.jpg;type=image/jpeg" `
  -F "category_hint=toothpaste"
```

También se puede abrir Swagger, expandir `POST /analyze`, pulsar **Try it out** y
seleccionar las fotografías. Se valida el contenido real con Pillow, no solamente
el nombre. Cada archivo admite como máximo 10 MB por defecto y nunca se persiste:
solo se procesa en memoria y se envía al proveedor configurado. No se registra el
binario ni su base64.

## Respuesta de `/analyze`

```json
{
  "analysis": {
    "images_received": 2,
    "detections_total": 3,
    "duplicates_removed": 1,
    "rankable_count": 1,
    "needs_confirmation_count": 1,
    "unsupported_count": 0
  },
  "rankings": {"toothpaste": [{"position": 1, "product": {}, "normalized_price": 2285.71, "comparison_quantity": 100, "comparison_unit": "g", "display_unit": "100 g", "savings_vs_next": null}]},
  "rankable_products": [],
  "needs_confirmation": [],
  "unsupported_products": [],
  "warnings": []
}
```

`rankable_products` contiene únicamente instancias válidas del modelo estricto de
v0.1. `needs_confirmation` conserva candidatos con baja confianza (`< 0.75`),
datos ausentes/ambiguos, asociación precio-producto dudosa, promociones o precios
condicionados. `unsupported_products` conserva categorías futuras. Los candidatos
incluyen `source_image_index`, texto original, confidence, issues y bounding boxes
cuando el proveedor puede obtenerlos.

Las fotos superpuestas se deduplican conservadoramente usando marca, nombre,
variante, cantidad, unidad y precio; se conserva la detección de mayor confianza.
No se fusionan productos solo por compartir marca. El descartado queda auditable
en `needs_confirmation` con `DUPLICATE_CANDIDATE`.

## Errores

- `400`: cantidad de archivos o imagen inválida.
- `413`: archivo demasiado grande.
- `415`: medio no soportado o contenido distinto al tipo declarado.
- `422`: hint inválido o validación HTTP.
- `502`: fallo/respuesta inválida del proveedor.
- `503`: proveedor desconocido o clave ausente.
- `504`: timeout externo.

No se devuelve un ranking alternativo o inventado cuando el proveedor falla.

## Pruebas

```bash
python -m pytest -q
python -m compileall -q app tests
git diff --check
```

Las pruebas normales usan Pillow, mocks e inyección; no necesitan una clave ni
hacen llamadas externas. La integración real es explícitamente opt-in:

```bash
RUN_LIVE_VISION_TESTS=1 OPENAI_API_KEY='...' \
  VISION_PROVIDER=openai python -m pytest -m live -q
```

## Limitaciones y próximo paso

La calidad depende de iluminación, resolución, oclusión, perspectiva y legibilidad
de etiquetas. La deduplicación v0.2 es textual, no geométrica; tampoco hace OCR
especializado, escaneo de códigos, persistencia o corrección interactiva. Una v0.3
debería incorporar una interfaz de revisión que muestre bounding boxes, corrección
manual, mejor emparejamiento espacial producto–precio y métricas con un conjunto
propio de imágenes autorizadas. APK, frontend completo y autenticación quedan
fuera de este alcance.
