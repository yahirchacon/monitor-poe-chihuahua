# Alimentador RSS V8 — Periódico Oficial del Estado de Chihuahua

Consulta directamente el índice oficial de periódicos y anexos de Chihuahua en
<https://chihuahua.gob.mx/periodicooficial/buscador> y publica un RSS compatible
con el conector estándar de Power Automate. **No es un sitio oficial del gobierno**.

## Requisitos

- Cuenta gratuita de GitHub; repositorio **público**.
- GitHub Pages habilitado con **GitHub Actions**.
- El ZIP `Monitor_Noticias_Chihuahua_Federacion_V8.zip` (paquete heredado importable)
  se importa por separado en Microsoft Power Automate.

## Publicación en GitHub Pages

1. Crea un repositorio público llamado `monitor-poe-chihuahua` en GitHub.
2. Coloca en la raíz `poe_feed.py`, `requirements.txt` y la carpeta `.github/workflows/`
   de este paquete respetando exactamente su estructura; se puede hacer por GitHub
   Desktop o `git` (instrucciones abajo).
3. En el repositorio, **Settings > Pages > Build and deployment > Source**,
   selecciona **GitHub Actions**.
4. En **Actions > Actualizar RSS oficial POE Chihuahua > Run workflow**, ejecuta
   una vez. Espera a que finalice sin errores (verde).
5. Comprueba estas URLs cambiando `TU_USUARIO` por el identificador de GitHub:
   - `https://TU_USUARIO.github.io/monitor-poe-chihuahua/feed.xml`
   - `https://TU_USUARIO.github.io/monitor-poe-chihuahua/estado.json`
6. En Power Automate V8, abre la variable `Inicializar_URL_RSS_POE_Directo` y
   pega exactamente la primera URL. Guarda y ejecuta una prueba.

Si lo prefieres con línea de comandos (después de crear el repositorio vacío):

```bash
git init
git add .
git commit -m "RSS Periódico Oficial Chihuahua V8"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/monitor-poe-chihuahua.git
git push -u origin main
```

## Qué detecta

- Los ejemplares oficiales de **hoy y ayer**, usando la fecha que aparece impresa
  en el catálogo; no usa la fecha en que Google indexó un PDF.
- Los anexos de esas ediciones sobre participaciones, aportaciones, Hacienda,
  deuda, finanzas, presupuestos, ingresos, egresos, contabilidad gubernamental,
  fiscalización, legislación y administración pública.
- Cada entrada contiene **un solo enlace al documento original** en el dominio
  del Gobierno de Chihuahua.

El script lee las primeras dos páginas del índice público. Si la estructura
cambia o no puede interpretar las fechas, la ejecución **falla claramente** en
GitHub Actions, en lugar de publicar un resultado vacío por error. La página
anterior puede continuar disponible: Power Automate aplicará además su propio
filtro de hoy y ayer.

## Frecuencia y fecha

GitHub Actions actualiza cada hora a los 15 minutos (puede retrasarse por
carga de GitHub). El flujo Power Automate corre una sola vez al día, a las
10:00, hora de Chihuahua. Publicaciones oficiales que aparezcan después de
las 10:00 se recogen en la ejecución del día siguiente. No se recuperarán si
se publican con más de un día natural de antigüedad.

## Limitaciones honestas

- La extracción de los anexos se basa en **títulos y enlaces** publicados en el
  catálogo, no en texto íntegro ni resumen de los PDF.
- Si el portal cambia HTML, diseño o bloquea consultas automatizadas, hay que
  ajustar `poe_feed.py`.
- GitHub Pages es público: el RSS solo debe contener enlaces a información
  **pública** del portal oficial. No se incluyen correos ni datos privados.
- GitHub Actions no asegura una hora exacta; el proceso se ejecuta con la
  frecuencia disponible y registra errores en **Actions**.
- El RSS de los periódicos genera cada día una ventana de hoy y ayer; Power
  Automate aplica de nuevo la fecha de publicación para impedir rezagos.

## Pruebas locales

```bash
python -m pip install -r requirements.txt
python -m pip install pytest
python -m pytest -q
python poe_feed.py
```

El último comando requiere internet. Para probar fechas en un entorno controlado,
puede establecerse `V8_FECHA_PRUEBA=2026-10-15`; no se debe dejar esa variable
activada en producción.
