from fastapi import FastAPI, Depends, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from sqlalchemy.orm import Session
from docxtpl import DocxTemplate
import os
import json
import subprocess
import platform # <-- Nueva importación para detectar el Sistema Operativo
import models, database

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="USAER Digital - Gestión de Expedientes")
templates = Jinja2Templates(directory="templates")

DEFAULT_PARTICIPANTES = [
    {"nombre": "Lic. Luz María Gálvez Lara", "area": "Maestra de Apoyo"},
    {"nombre": "Lic. Ana Renee Salomon Aguirre", "area": "Área de Psicología"},
    {"nombre": "Lic. Graciela Martínez Pazos", "area": "Área de Trabajo Social"},
    {"nombre": "Lic. Rocío Aidé Amatón Lugo", "area": "Área de comunicación"},
    {"nombre": "Lic. Liliana Guadalupe Soto Romero", "area": "Área de psicomotricidad"},
    {"nombre": "Lic.Ruth Noemi Armendáriz García", "area": "Directora USAER 7505"}
]

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(database.get_db)):
    alumnos = db.query(models.Alumno).all()
    return templates.TemplateResponse(request=request, name="dashboard.html", context={"alumnos": alumnos})

@app.post("/alumnos/nuevo")
async def crear_alumno(
    nombre: str = Form(...), edad: str = Form(...), escuela: str = Form(...), grado_grupo: str = Form(...), 
    db: Session = Depends(database.get_db)
):
    nuevo_alumno = models.Alumno(nombre=nombre, edad=edad, escuela=escuela, grado_grupo=grado_grupo)
    db.add(nuevo_alumno)
    db.commit()
    db.refresh(nuevo_alumno)
    
    nuevo_informe = models.InformeDeteccion(
        alumno_id=nuevo_alumno.id,
        participantes=json.dumps(DEFAULT_PARTICIPANTES),
        planeacion="[]"
    )
    db.add(nuevo_informe)
    db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.get("/informe/{informe_id}", response_class=HTMLResponse)
async def ver_informe(request: Request, informe_id: int, db: Session = Depends(database.get_db)):
    informe = db.query(models.InformeDeteccion).filter(models.InformeDeteccion.id == informe_id).first()
    parts = json.loads(informe.participantes) if informe.participantes else []
    plan = json.loads(informe.planeacion) if informe.planeacion and informe.planeacion != "[]" else [{"r":"","i":"","fe":"","fr":"","o":""} for _ in range(8)]
    return templates.TemplateResponse(request=request, name="informe.html", context={"informe": informe, "participantes": parts, "planeacion": plan})

@app.patch("/api/informe/{informe_id}")
async def guardar_progreso(informe_id: int, request: Request, db: Session = Depends(database.get_db)):
    form_data = await request.form()
    informe = db.query(models.InformeDeteccion).filter(models.InformeDeteccion.id == informe_id).first()
    if not informe:
        return HTMLResponse("Error: Informe no encontrado", status_code=404)

    campos_texto = ['docente', 'fecha_elaboracion', 'condicion_discapacidad', 'antecedentes_escolares', 'evaluacion_inicial', 'area_comunicativa', 'area_motriz', 'requiere_evaluacion', 'motivo_evaluacion']
    for campo in campos_texto:
        if campo in form_data:
            setattr(informe, campo, form_data[campo])

    if 'part_nombre[]' in form_data:
        nombres = form_data.getlist('part_nombre[]')
        areas = form_data.getlist('part_area[]')
        parts = [{"nombre": n, "area": a} for n, a in zip(nombres, areas) if n.strip() or a.strip()]
        informe.participantes = json.dumps(parts)
    else:
        informe.participantes = "[]"

    if 'plan_resp[]' in form_data:
        resps = form_data.getlist('plan_resp[]')
        insts = form_data.getlist('plan_inst[]')
        fechas_eval = form_data.getlist('plan_fecha_eval[]')
        fechas_res = form_data.getlist('plan_fecha_res[]')
        obs = form_data.getlist('plan_obs[]')
        
        planeacion_list = []
        for i in range(8):
            planeacion_list.append({
                "r": resps[i] if i < len(resps) else "",
                "i": insts[i] if i < len(insts) else "",
                "fe": fechas_eval[i] if i < len(fechas_eval) else "",
                "fr": fechas_res[i] if i < len(fechas_res) else "",
                "o": obs[i] if i < len(obs) else ""
            })
        informe.planeacion = json.dumps(planeacion_list)

    db.commit()
    return HTMLResponse('<span class="text-xs text-blue-500 font-semibold animate-pulse">✓ Guardado</span>')

@app.get("/api/informe/{informe_id}/exportar")
async def exportar_pdf(informe_id: int, db: Session = Depends(database.get_db)):
    informe = db.query(models.InformeDeteccion).filter(models.InformeDeteccion.id == informe_id).first()
    doc = DocxTemplate("plantillas/plantilla_idi.docx")
    plan_data = json.loads(informe.planeacion) if informe.planeacion and informe.planeacion != "[]" else [{"r":"","i":"","fe":"","fr":"","o":""} for _ in range(8)]
    
    contexto = {
        "nombre": informe.alumno.nombre,
        "edad": informe.alumno.edad,
        "escuela": informe.alumno.escuela,
        "grado_grupo": informe.alumno.grado_grupo,
        "docente": informe.docente or "",
        "fecha_elaboracion": informe.fecha_elaboracion or "",
        "motivo_evaluacion": informe.motivo_evaluacion or "",
        "condicion_discapacidad": informe.condicion_discapacidad or "",
        "antecedentes_escolares": informe.antecedentes_escolares or "",
        "evaluacion_inicial": informe.evaluacion_inicial or "",
        "area_comunicativa": informe.area_comunicativa or "",
        "area_motriz": informe.area_motriz or "",
        "req_si": "X" if informe.requiere_evaluacion == "Sí" else "",
        "req_no": "X" if informe.requiere_evaluacion == "No" else "",
        "participantes": json.loads(informe.participantes) if informe.participantes else [],
        **{f"p{i+1}_r": row["r"] for i, row in enumerate(plan_data)},
        **{f"p{i+1}_i": row["i"] for i, row in enumerate(plan_data)},
        **{f"p{i+1}_fe": row["fe"] for i, row in enumerate(plan_data)},
        **{f"p{i+1}_fr": row["fr"] for i, row in enumerate(plan_data)},
        **{f"p{i+1}_o": row["o"] for i, row in enumerate(plan_data)},
    }
    
    doc.render(contexto)
    safe_name = informe.alumno.nombre.replace(" ", "_")
    docx_filename = f"Informe_{safe_name}.docx"
    pdf_filename = f"Informe_{safe_name}.pdf"
    
    ruta_docx = os.path.abspath(docx_filename)
    ruta_pdf = os.path.abspath(pdf_filename)
    doc.save(ruta_docx)
    
    # --- LOGICA INTELIGENTE DE SISTEMA OPERATIVO ---
    try:
        if platform.system() == "Windows":
            # Entorno de desarrollo local (Tu PC)
            from docx2pdf import convert as convert_pdf
            convert_pdf(ruta_docx, ruta_pdf)
        else:
            # Entorno Docker (Linux)
            subprocess.run([
                "libreoffice", "--headless", "--convert-to", "pdf",
                ruta_docx, "--outdir", os.path.dirname(ruta_docx)
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"Error en conversión: {e}")
        return HTMLResponse(f"Error generando el PDF. Detalle: {e}", status_code=500)
    
    return FileResponse(ruta_pdf, filename=pdf_filename, media_type='application/pdf')