from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Alumno(Base):
    __tablename__ = "alumnos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True)
    edad = Column(String)
    escuela = Column(String)
    grado_grupo = Column(String)

    informes = relationship("InformeDeteccion", back_populates="alumno")


class InformeDeteccion(Base):
    __tablename__ = "informes_deteccion"

    id = Column(Integer, primary_key=True, index=True)
    alumno_id = Column(Integer, ForeignKey("alumnos.id"))
    
    # Encabezado y Motivo
    docente = Column(String, nullable=True)
    fecha_elaboracion = Column(String, nullable=True)
    motivo_evaluacion = Column(String, nullable=True)
    
    # Áreas de texto largo
    condicion_discapacidad = Column(Text, nullable=True)
    antecedentes_escolares = Column(Text, nullable=True)
    evaluacion_inicial = Column(Text, nullable=True)
    area_comunicativa = Column(Text, nullable=True)
    area_motriz = Column(Text, nullable=True)
    requiere_evaluacion = Column(String, default="No")
    
    # Tablas (Guardadas internamente como texto JSON)
    participantes = Column(Text, default="[]")
    planeacion = Column(Text, default="[]")

    alumno = relationship("Alumno", back_populates="informes")