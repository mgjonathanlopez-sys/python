#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gestor local y configurable de proyectos de investigación."""

from __future__ import annotations
import csv, html, json, os, shutil, sqlite3, subprocess, sys, webbrowser, zipfile
from datetime import date, datetime, timedelta
from pathlib import Path

from PySide6.QtCore import Qt, QDate, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QFont
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDateEdit, QDialog, QDialogButtonBox,
    QFileDialog, QFormLayout, QFrame, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
    QProgressBar, QPushButton, QSpinBox, QSplitter, QStackedWidget, QTableWidget,
    QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget
)
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, create_engine, func, or_, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

APP_TITLE = "Gestor de Proyectos de Investigación"
STATUSES = ["No iniciada", "En progreso", "Terminada", "Bloqueada"]
PRIORITIES = ["Baja", "Media", "Alta", "Crítica"]
MODULES = [
    ("Dashboard", "dashboard"), ("Proyectos", "projects"), ("Plan de trabajo", "tasks"),
    ("Cronograma / Gantt", "gantt"), ("Evidencias", "evidence"),
    ("Gestión documental", "documents"), ("Revisión sistemática", "review"),
    ("Instrumentos", "instruments"), ("Organizaciones", "organizations"),
    ("Trabajo de campo", "fieldwork"), ("Análisis", "analysis"),
    ("Taller participativo", "workshop"), ("AHP", "ahp"),
    ("Indicadores", "indicators"), ("Productos", "products"),
    ("Informes", "reports"), ("Alertas", "alerts"), ("Auditoría", "audit"),
    ("Configuración", "settings"),
]

def app_root() -> Path:
    if sys.platform.startswith("win"):
        base = Path(os.getenv("LOCALAPPDATA", Path.home()))
    else:
        base = Path.home() / ".local" / "share"
    root = base / "ResearchProjectManager"
    for folder in ("evidencias", "documentos", "reportes", "respaldos"):
        (root / folder).mkdir(parents=True, exist_ok=True)
    return root

ROOT = app_root()
DB_PATH = ROOT / "gestor_proyectos.sqlite"

class Base(DeclarativeBase):
    pass

class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(80), default="")
    name: Mapped[str] = mapped_column(String(300))
    location: Mapped[str] = mapped_column(String(200), default="")
    principal_investigator: Mapped[str] = mapped_column(String(200), default="")
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    phase: Mapped[str] = mapped_column(String(180))
    code: Mapped[str] = mapped_column(String(40), unique=True)
    title: Mapped[str] = mapped_column(String(500))
    responsible: Mapped[str] = mapped_column(String(200), default="")
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(40), default="No iniciada")
    priority: Mapped[str] = mapped_column(String(30), default="Media")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    predecessor: Mapped[str] = mapped_column(String(100), default="")
    expected_result: Mapped[str] = mapped_column(Text, default="")
    product_link: Mapped[str] = mapped_column(String(200), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    evidence_required: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    evidence: Mapped[list["Evidence"]] = relationship(cascade="all, delete-orphan", back_populates="task")

class Evidence(Base):
    __tablename__ = "evidence"
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"))
    name: Mapped[str] = mapped_column(String(300))
    category: Mapped[str] = mapped_column(String(100), default="Documento")
    source_path: Mapped[str] = mapped_column(Text, default="")
    stored_path: Mapped[str] = mapped_column(Text)
    notes: Mapped[str] = mapped_column(Text, default="")
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    task: Mapped[Task] = relationship(back_populates="evidence")

class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    anonymous_code: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(300), default="")
    sector: Mapped[str] = mapped_column(String(150), default="")
    size: Mapped[str] = mapped_column(String(50), default="")
    municipality: Mapped[str] = mapped_column(String(150), default="")
    contact_name: Mapped[str] = mapped_column(String(200), default="")
    phone: Mapped[str] = mapped_column(String(80), default="")
    email: Mapped[str] = mapped_column(String(200), default="")
    participation_status: Mapped[str] = mapped_column(String(80), default="Sin contactar")
    consent: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

class ModuleRecord(Base):
    __tablename__ = "module_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    module: Mapped[str] = mapped_column(String(80))
    code: Mapped[str] = mapped_column(String(80), default="")
    title: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(80), default="Pendiente")
    responsible: Mapped[str] = mapped_column(String(200), default="")
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    details: Mapped[str] = mapped_column(Text, default="")
    file_path: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

class Audit(Base):
    __tablename__ = "audit"
    id: Mapped[int] = mapped_column(primary_key=True)
    entity: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[int] = mapped_column(Integer, default=0)
    action: Mapped[str] = mapped_column(String(80))
    detail: Mapped[str] = mapped_column(Text, default="")
    happened_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

engine = create_engine(f"sqlite:///{DB_PATH}", future=True)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine, expire_on_commit=False)

def project(session):
    return session.scalars(select(Project).order_by(Project.id)).first()

def audit(session, entity, entity_id, action, detail=""):
    session.add(Audit(entity=entity, entity_id=entity_id or 0, action=action, detail=detail))

def cell(value):
    item = QTableWidgetItem("" if value is None else str(value))
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    return item

def open_local(path):
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

class ProjectDialog(QDialog):
    def __init__(self, parent=None, current=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración del proyecto")
        self.setMinimumWidth(520)
        form = QFormLayout(self)
        self.code = QLineEdit(current.code if current else "")
        self.name = QLineEdit(current.name if current else "")
        self.location = QLineEdit(current.location if current else "")
        self.pi = QLineEdit(current.principal_investigator if current else "")
        self.start = QDateEdit(calendarPopup=True)
        self.end = QDateEdit(calendarPopup=True)
        self.start.setDisplayFormat("yyyy-MM-dd"); self.end.setDisplayFormat("yyyy-MM-dd")
        if current:
            self.start.setDate(QDate(current.start_date.year,current.start_date.month,current.start_date.day))
            self.end.setDate(QDate(current.end_date.year,current.end_date.month,current.end_date.day))
        else:
            self.start.setDate(QDate.currentDate()); self.end.setDate(QDate.currentDate().addYears(1))
        for label, widget in [
            ("Código",self.code),("Nombre del proyecto",self.name),("Territorio",self.location),
            ("Investigador principal",self.pi),("Fecha de inicio",self.start),("Fecha de cierre",self.end)]:
            form.addRow(label,widget)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.validate); buttons.rejected.connect(self.reject); form.addRow(buttons)
    def validate(self):
        if not self.name.text().strip():
            QMessageBox.warning(self,"Dato obligatorio","Escriba el nombre del proyecto."); return
        if self.end.date()<self.start.date():
            QMessageBox.warning(self,"Fechas","La fecha final debe ser posterior a la inicial."); return
        self.accept()
    def values(self):
        return dict(code=self.code.text().strip(),name=self.name.text().strip(),
            location=self.location.text().strip(),principal_investigator=self.pi.text().strip(),
            start_date=self.start.date().toPython(),end_date=self.end.date().toPython())

class TaskDialog(QDialog):
    def __init__(self,parent=None,current=None,project_obj=None):
        super().__init__(parent); self.setWindowTitle("Actividad"); self.setMinimumWidth(650)
        form=QFormLayout(self)
        self.phase=QLineEdit(current.phase if current else "")
        self.code=QLineEdit(current.code if current else "")
        self.title_edit=QLineEdit(current.title if current else "")
        self.responsible=QLineEdit(current.responsible if current else "")
        self.start=QDateEdit(calendarPopup=True); self.end=QDateEdit(calendarPopup=True)
        self.start.setDisplayFormat("yyyy-MM-dd"); self.end.setDisplayFormat("yyyy-MM-dd")
        default_start=current.start_date if current else (project_obj.start_date if project_obj else date.today())
        default_end=current.end_date if current else default_start
        self.start.setDate(QDate(default_start.year,default_start.month,default_start.day))
        self.end.setDate(QDate(default_end.year,default_end.month,default_end.day))
        self.status=QComboBox(); self.status.addItems(STATUSES)
        self.priority=QComboBox(); self.priority.addItems(PRIORITIES)
        if current:self.status.setCurrentText(current.status);self.priority.setCurrentText(current.priority)
        self.progress=QSpinBox();self.progress.setRange(0,100);self.progress.setSuffix(" %")
        self.progress.setValue(current.progress if current else 0)
        self.predecessor=QLineEdit(current.predecessor if current else "")
        self.result=QLineEdit(current.expected_result if current else "")
        self.product=QLineEdit(current.product_link if current else "")
        self.notes=QTextEdit(current.notes if current else "");self.notes.setFixedHeight(80)
        self.required=QCheckBox("Exigir evidencia para acreditar cumplimiento")
        self.required.setChecked(current.evidence_required if current else True)
        fields=[("Fase",self.phase),("Código",self.code),("Actividad",self.title_edit),
            ("Responsable",self.responsible),("Fecha de inicio",self.start),("Fecha de fin",self.end),
            ("Estado",self.status),("Prioridad",self.priority),("Avance",self.progress),
            ("Predecesora",self.predecessor),("Resultado esperado",self.result),
            ("Producto relacionado",self.product),("Observaciones",self.notes),("",self.required)]
        for label,w in fields:form.addRow(label,w)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.validate);buttons.rejected.connect(self.reject);form.addRow(buttons)
    def validate(self):
        if not self.phase.text().strip() or not self.code.text().strip() or not self.title_edit.text().strip():
            QMessageBox.warning(self,"Datos obligatorios","Fase, código y actividad son obligatorios.");return
        if self.end.date()<self.start.date():
            QMessageBox.warning(self,"Fechas","La fecha final debe ser posterior a la inicial.");return
        self.accept()
    def values(self):
        return dict(phase=self.phase.text().strip(),code=self.code.text().strip(),
            title=self.title_edit.text().strip(),responsible=self.responsible.text().strip(),
            start_date=self.start.date().toPython(),end_date=self.end.date().toPython(),
            status=self.status.currentText(),priority=self.priority.currentText(),
            progress=self.progress.value(),predecessor=self.predecessor.text().strip(),
            expected_result=self.result.text().strip(),product_link=self.product.text().strip(),
            notes=self.notes.toPlainText().strip(),evidence_required=self.required.isChecked(),
            updated_at=datetime.now())

class OrganizationDialog(QDialog):
    def __init__(self,parent=None,current=None):
        super().__init__(parent);self.setWindowTitle("Organización participante");self.setMinimumWidth(560)
        form=QFormLayout(self);self.inputs={}
        fields=[("Código anonimizado","anonymous_code"),("Nombre","name"),("Sector","sector"),
            ("Tamaño","size"),("Municipio","municipality"),("Contacto","contact_name"),
            ("Teléfono","phone"),("Correo","email"),("Estado de participación","participation_status")]
        for label,key in fields:
            w=QLineEdit(getattr(current,key,"") or "");self.inputs[key]=w;form.addRow(label,w)
        self.consent=QCheckBox("Consentimiento registrado");self.consent.setChecked(bool(current and current.consent))
        self.notes=QTextEdit(getattr(current,"notes","") or "");self.notes.setFixedHeight(80)
        form.addRow("",self.consent);form.addRow("Observaciones",self.notes)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.validate);buttons.rejected.connect(self.reject);form.addRow(buttons)
    def validate(self):
        if not self.inputs["anonymous_code"].text().strip():
            QMessageBox.warning(self,"Dato obligatorio","El código anonimizado es obligatorio.");return
        self.accept()
    def values(self):
        d={k:w.text().strip() for k,w in self.inputs.items()}
        d.update(consent=self.consent.isChecked(),notes=self.notes.toPlainText().strip(),updated_at=datetime.now())
        return d

class DashboardPage(QWidget):
    def __init__(self,window):
        super().__init__();self.window=window
        layout=QVBoxLayout(self);title=QLabel("Resumen ejecutivo");title.setObjectName("PageTitle");layout.addWidget(title)
        cards=QHBoxLayout();self.card_values=[]
        for caption in ("Cumplimiento","Actividades","Vencidas","Próximas","Evidencias","Organizaciones"):
            frame=QFrame();frame.setObjectName("Card");box=QVBoxLayout(frame)
            value=QLabel("0");value.setObjectName("CardValue");cap=QLabel(caption)
            box.addWidget(value);box.addWidget(cap);cards.addWidget(frame);self.card_values.append(value)
        layout.addLayout(cards)
        self.table=QTableWidget(0,5);self.table.setHorizontalHeaderLabels(
            ["Fase","Actividades","Terminadas","Con evidencia","Cumplimiento"])
        self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
    def refresh(self):
        with Session() as s:
            tasks=s.scalars(select(Task)).all()
            evid={i:n for i,n in s.execute(select(Evidence.task_id,func.count(Evidence.id)).group_by(Evidence.task_id))}
            def compliant(t):return t.status=="Terminada" and (not t.evidence_required or evid.get(t.id,0)>0)
            total=len(tasks);done=sum(compliant(t) for t in tasks)
            overdue=sum(t.end_date<date.today() and not compliant(t) for t in tasks)
            upcoming=sum(date.today()<=t.end_date<=date.today()+timedelta(days=14) and not compliant(t) for t in tasks)
            vals=[f"{round(done*100/total) if total else 0}%",total,overdue,upcoming,
                  sum(evid.values()),s.scalar(select(func.count(Organization.id))) or 0]
            for label,value in zip(self.card_values,vals):label.setText(str(value))
            phases={}
            for t in tasks:phases.setdefault(t.phase,[]).append(t)
            self.table.setRowCount(len(phases))
            for row,(phase,items) in enumerate(sorted(phases.items())):
                finished=sum(i.status=="Terminada" for i in items);ok=sum(compliant(i) for i in items)
                data=[phase,len(items),finished,sum(evid.get(i.id,0)>0 for i in items),
                      f"{round(ok*100/len(items))}%"]
                for col,value in enumerate(data):self.table.setItem(row,col,cell(value))

class TaskPage(QWidget):
    changed=Signal()
    def __init__(self,window):
        super().__init__();self.window=window
        layout=QVBoxLayout(self);head=QHBoxLayout()
        title=QLabel("Plan de trabajo");title.setObjectName("PageTitle");head.addWidget(title);head.addStretch()
        self.search=QLineEdit();self.search.setPlaceholderText("Buscar código, actividad o responsable…")
        self.filter=QComboBox();self.filter.addItems(["Todos"]+STATUSES)
        for text,fn in [("Importar CSV",self.import_csv),("Nueva",self.add),("Editar",self.edit),("Eliminar",self.delete)]:
            b=QPushButton(text);b.clicked.connect(fn);head.addWidget(b)
        head.insertWidget(2,self.search);head.insertWidget(3,self.filter);layout.addLayout(head)
        self.table=QTableWidget(0,9);self.table.setHorizontalHeaderLabels(
            ["Código","Fase","Actividad","Responsable","Inicio","Fin","Estado","Avance","Evidencias"])
        self.table.horizontalHeader().setSectionResizeMode(2,QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self.edit);layout.addWidget(self.table)
        self.search.textChanged.connect(self.refresh);self.filter.currentTextChanged.connect(self.refresh)
    def selected(self):
        row=self.table.currentRow()
        return int(self.table.item(row,0).data(Qt.ItemDataRole.UserRole)) if row>=0 else None
    def refresh(self):
        with Session() as s:
            q=select(Task)
            text=self.search.text().strip()
            if text:q=q.where(or_(Task.code.contains(text),Task.title.contains(text),Task.responsible.contains(text)))
            if self.filter.currentText()!="Todos":q=q.where(Task.status==self.filter.currentText())
            rows=s.scalars(q.order_by(Task.start_date,Task.code)).all()
            self.table.setRowCount(len(rows))
            for r,t in enumerate(rows):
                vals=[t.code,t.phase,t.title,t.responsible,t.start_date,t.end_date,t.status,f"{t.progress}%",len(t.evidence)]
                for c,v in enumerate(vals):
                    it=cell(v);self.table.setItem(r,c,it)
                    if c==0:it.setData(Qt.ItemDataRole.UserRole,t.id)
                if t.end_date<date.today() and t.status!="Terminada":
                    for c in range(9):self.table.item(r,c).setBackground(QColor("#FFE8E8"))
    def add(self):
        with Session() as s:
            p=project(s)
            if not p:return self.window.configure_project()
            d=TaskDialog(self,project_obj=p)
            if d.exec():
                try:
                    t=Task(project_id=p.id,**d.values());s.add(t);s.flush();audit(s,"task",t.id,"crear",t.code);s.commit()
                except Exception as e:s.rollback();QMessageBox.critical(self,"No se pudo guardar",str(e));return
        self.window.refresh_all()
    def edit(self):
        tid=self.selected()
        if not tid:return
        with Session() as s:
            t=s.get(Task,tid);d=TaskDialog(self,current=t,project_obj=project(s))
            if d.exec():
                try:
                    for k,v in d.values().items():setattr(t,k,v)
                    audit(s,"task",t.id,"actualizar",t.code);s.commit()
                except Exception as e:s.rollback();QMessageBox.critical(self,"No se pudo guardar",str(e));return
        self.window.refresh_all()
    def delete(self):
        tid=self.selected()
        if not tid:return
        if QMessageBox.question(self,"Confirmar","¿Eliminar la actividad y sus registros de evidencia?")!=QMessageBox.StandardButton.Yes:return
        with Session() as s:
            t=s.get(Task,tid);audit(s,"task",tid,"eliminar",t.code);s.delete(t);s.commit()
        self.window.refresh_all()
    def import_csv(self):
        path,_=QFileDialog.getOpenFileName(self,"Importar actividades","","CSV (*.csv)")
        if not path:return
        with Session() as s:
            p=project(s)
            if not p:return self.window.configure_project()
            added=errors=0
            try:
                with open(path,encoding="utf-8-sig",newline="") as f:
                    for row in csv.DictReader(f):
                        try:
                            req=str(row.get("evidencia_requerida","si")).strip().lower() not in ("no","0","false")
                            t=Task(project_id=p.id,phase=row["fase"].strip(),code=row["codigo"].strip(),
                              title=row["actividad"].strip(),responsible=row.get("responsable","").strip(),
                              start_date=date.fromisoformat(row["fecha_inicio"]),end_date=date.fromisoformat(row["fecha_fin"]),
                              status=row.get("estado","No iniciada") or "No iniciada",
                              priority=row.get("prioridad","Media") or "Media",progress=int(row.get("avance",0) or 0),
                              predecessor=row.get("predecesora",""),expected_result=row.get("resultado_esperado",""),
                              evidence_required=req,notes=row.get("observaciones",""))
                            s.add(t);s.flush();added+=1
                        except Exception:errors+=1;s.rollback()
                audit(s,"task",0,"importar",f"{added} actividades");s.commit()
            except Exception as e:QMessageBox.critical(self,"Importación",str(e));return
        QMessageBox.information(self,"Importación",f"Actividades importadas: {added}\nFilas con error: {errors}")
        self.window.refresh_all()

class GanttPage(QWidget):
    def __init__(self,window):
        super().__init__();self.window=window
        layout=QVBoxLayout(self);title=QLabel("Cronograma / Gantt");title.setObjectName("PageTitle");layout.addWidget(title)
        note=QLabel("Vista temporal por meses. Las barras representan la duración planeada de cada actividad.")
        layout.addWidget(note);self.table=QTableWidget();layout.addWidget(self.table)
    def refresh(self):
        with Session() as s:
            rows=s.scalars(select(Task).order_by(Task.start_date,Task.code)).all()
            if not rows:self.table.setRowCount(0);self.table.setColumnCount(0);return
            start=min(t.start_date for t in rows).replace(day=1);end=max(t.end_date for t in rows)
            months=[];d=start
            while d<=end:
                months.append(d)
                d=date(d.year+1,1,1) if d.month==12 else date(d.year,d.month+1,1)
            self.table.setColumnCount(3+len(months));self.table.setRowCount(len(rows))
            self.table.setHorizontalHeaderLabels(["Código","Fase","Actividad"]+[m.strftime("%Y-%m") for m in months])
            self.table.horizontalHeader().setSectionResizeMode(2,QHeaderView.ResizeMode.Stretch)
            for r,t in enumerate(rows):
                for c,v in enumerate((t.code,t.phase,t.title)):self.table.setItem(r,c,cell(v))
                for j,m in enumerate(months):
                    mend=date(m.year+1,1,1)-timedelta(days=1) if m.month==12 else date(m.year,m.month+1,1)-timedelta(days=1)
                    active=t.start_date<=mend and t.end_date>=m
                    it=cell("■" if active else "")
                    if active:it.setBackground(QColor("#4DA3D9"));it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.table.setItem(r,3+j,it)

class EvidencePage(QWidget):
    def __init__(self,window):
        super().__init__();self.window=window
        layout=QVBoxLayout(self);head=QHBoxLayout();title=QLabel("Repositorio de evidencias");title.setObjectName("PageTitle")
        self.combo=QComboBox();self.combo.setMinimumWidth(500)
        add=QPushButton("Adjuntar evidencia");add.clicked.connect(self.add)
        head.addWidget(title);head.addStretch();head.addWidget(self.combo);head.addWidget(add);layout.addLayout(head)
        self.table=QTableWidget(0,4);self.table.setHorizontalHeaderLabels(["Archivo","Categoría","Fecha","Ubicación"])
        self.table.horizontalHeader().setSectionResizeMode(3,QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows);layout.addWidget(self.table)
        bar=QHBoxLayout()
        for text,fn in [("Abrir archivo",self.open),("Abrir carpeta",lambda:open_local(ROOT/"evidencias")),("Eliminar",self.delete)]:
            b=QPushButton(text);b.clicked.connect(fn);bar.addWidget(b)
        bar.addStretch();layout.addLayout(bar);self.combo.currentIndexChanged.connect(self.refresh_table)
    def refresh(self):
        current=self.combo.currentData();self.combo.blockSignals(True);self.combo.clear()
        with Session() as s:
            for t in s.scalars(select(Task).order_by(Task.start_date,Task.code)):
                self.combo.addItem(f"{t.code} | {t.title}",t.id)
        ix=self.combo.findData(current);self.combo.setCurrentIndex(ix if ix>=0 else 0);self.combo.blockSignals(False)
        self.refresh_table()
    def refresh_table(self):
        tid=self.combo.currentData()
        with Session() as s:rows=s.scalars(select(Evidence).where(Evidence.task_id==tid).order_by(Evidence.added_at.desc())).all() if tid else []
        self.table.setRowCount(len(rows))
        for r,e in enumerate(rows):
            for c,v in enumerate((e.name,e.category,e.added_at.strftime("%Y-%m-%d %H:%M"),e.stored_path)):
                it=cell(v);self.table.setItem(r,c,it)
                if c==0:it.setData(Qt.ItemDataRole.UserRole,e.id)
    def selected(self):
        r=self.table.currentRow();return self.table.item(r,0).data(Qt.ItemDataRole.UserRole) if r>=0 else None
    def add(self):
        tid=self.combo.currentData()
        if not tid:return QMessageBox.information(self,"Actividad","Primero cree o seleccione una actividad.")
        source,_=QFileDialog.getOpenFileName(self,"Seleccionar evidencia")
        if not source:return
        src=Path(source);folder=ROOT/"evidencias"/str(tid);folder.mkdir(exist_ok=True)
        target=folder/f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{src.name}"
        try:shutil.copy2(src,target)
        except OSError as e:return QMessageBox.critical(self,"Archivo",str(e))
        with Session() as s:
            ev=Evidence(task_id=tid,name=src.name,category="Documento",source_path=str(src),stored_path=str(target))
            s.add(ev);s.flush();audit(s,"evidence",ev.id,"adjuntar",src.name);s.commit()
        self.window.refresh_all()
    def open(self):
        eid=self.selected()
        if not eid:return
        with Session() as s:e=s.get(Evidence,eid);path=e.stored_path
        open_local(path)
    def delete(self):
        eid=self.selected()
        if not eid:return
        if QMessageBox.question(self,"Confirmar","¿Eliminar la copia local de esta evidencia?")!=QMessageBox.StandardButton.Yes:return
        with Session() as s:
            e=s.get(Evidence,eid);path=e.stored_path;audit(s,"evidence",eid,"eliminar",e.name);s.delete(e);s.commit()
        try:Path(path).unlink(missing_ok=True)
        except OSError:pass
        self.window.refresh_all()

class OrganizationPage(QWidget):
    def __init__(self,window):
        super().__init__();self.window=window
        layout=QVBoxLayout(self);head=QHBoxLayout();self.title=QLabel("Organizaciones participantes");self.title.setObjectName("PageTitle")
        head.addWidget(self.title);head.addStretch()
        for text,fn in [("Importar CSV",self.import_csv),("Nueva",self.add),("Editar",self.edit),("Eliminar",self.delete)]:
            b=QPushButton(text);b.clicked.connect(fn);head.addWidget(b)
        layout.addLayout(head);self.table=QTableWidget(0,7);self.table.setHorizontalHeaderLabels(
            ["Código","Organización","Sector","Tamaño","Municipio","Participación","Consentimiento"])
        self.table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows);layout.addWidget(self.table)
    def refresh(self):
        with Session() as s:rows=s.scalars(select(Organization).order_by(Organization.anonymous_code)).all()
        self.title.setText(f"Organizaciones participantes ({len(rows)})");self.table.setRowCount(len(rows))
        for r,o in enumerate(rows):
            for c,v in enumerate((o.anonymous_code,o.name,o.sector,o.size,o.municipality,o.participation_status,"Sí" if o.consent else "No")):
                it=cell(v);self.table.setItem(r,c,it)
                if c==0:it.setData(Qt.ItemDataRole.UserRole,o.id)
    def selected(self):
        r=self.table.currentRow();return self.table.item(r,0).data(Qt.ItemDataRole.UserRole) if r>=0 else None
    def add(self):
        with Session() as s:
            p=project(s)
            if not p:return self.window.configure_project()
            d=OrganizationDialog(self)
            if d.exec():
                try:o=Organization(project_id=p.id,**d.values());s.add(o);s.flush();audit(s,"organization",o.id,"crear",o.anonymous_code);s.commit()
                except Exception as e:s.rollback();return QMessageBox.critical(self,"No se pudo guardar",str(e))
        self.window.refresh_all()
    def edit(self):
        oid=self.selected()
        if not oid:return
        with Session() as s:
            o=s.get(Organization,oid);d=OrganizationDialog(self,o)
            if d.exec():
                for k,v in d.values().items():setattr(o,k,v)
                audit(s,"organization",o.id,"actualizar",o.anonymous_code);s.commit()
        self.window.refresh_all()
    def delete(self):
        oid=self.selected()
        if oid and QMessageBox.question(self,"Confirmar","¿Eliminar la organización?")==QMessageBox.StandardButton.Yes:
            with Session() as s:o=s.get(Organization,oid);audit(s,"organization",oid,"eliminar",o.anonymous_code);s.delete(o);s.commit()
            self.window.refresh_all()
    def import_csv(self):
        path,_=QFileDialog.getOpenFileName(self,"Importar organizaciones","","CSV (*.csv)")
        if not path:return
        with Session() as s:
            p=project(s)
            if not p:return self.window.configure_project()
            added=errors=0
            with open(path,encoding="utf-8-sig",newline="") as f:
                for row in csv.DictReader(f):
                    try:
                        yes=str(row.get("consentimiento","no")).lower() in ("si","sí","1","true")
                        o=Organization(project_id=p.id,anonymous_code=row["codigo_anonimo"].strip(),
                          name=row.get("nombre",""),sector=row.get("sector",""),size=row.get("tamano",""),
                          municipality=row.get("municipio",""),contact_name=row.get("contacto",""),
                          phone=row.get("telefono",""),email=row.get("correo",""),
                          participation_status=row.get("estado_participacion","Sin contactar"),
                          consent=yes,notes=row.get("observaciones",""))
                        s.add(o);s.flush();added+=1
                    except Exception:errors+=1;s.rollback()
            audit(s,"organization",0,"importar",f"{added} registros");s.commit()
        QMessageBox.information(self,"Importación",f"Registros importados: {added}\nFilas con error: {errors}")
        self.window.refresh_all()

class GenericDialog(QDialog):
    def __init__(self,parent=None,current=None,title="Registro"):
        super().__init__(parent);self.setWindowTitle(title);self.setMinimumWidth(560)
        form=QFormLayout(self)
        self.code=QLineEdit(getattr(current,"code","") or "");self.title_edit=QLineEdit(getattr(current,"title","") or "")
        self.status=QComboBox();self.status.addItems(["Pendiente","En progreso","Finalizado","Bloqueado"])
        if current:self.status.setCurrentText(current.status)
        self.responsible=QLineEdit(getattr(current,"responsible","") or "")
        self.due=QDateEdit(calendarPopup=True);self.due.setDisplayFormat("yyyy-MM-dd")
        d=getattr(current,"due_date",None) or date.today();self.due.setDate(QDate(d.year,d.month,d.day))
        self.details=QTextEdit(getattr(current,"details","") or "");self.details.setFixedHeight(120)
        self.file=QLineEdit(getattr(current,"file_path","") or "");browse=QPushButton("Seleccionar…")
        browse.clicked.connect(self.browse);file_row=QHBoxLayout();file_row.addWidget(self.file);file_row.addWidget(browse)
        for l,w in [("Código",self.code),("Título / descripción",self.title_edit),("Estado",self.status),
                    ("Responsable",self.responsible),("Fecha límite",self.due),("Detalles",self.details)]:form.addRow(l,w)
        form.addRow("Archivo relacionado",file_row)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.validate);buttons.rejected.connect(self.reject);form.addRow(buttons)
    def browse(self):
        path,_=QFileDialog.getOpenFileName(self,"Seleccionar archivo")
        if path:self.file.setText(path)
    def validate(self):
        if not self.title_edit.text().strip():return QMessageBox.warning(self,"Dato obligatorio","Escriba un título o descripción.")
        self.accept()
    def values(self):
        return dict(code=self.code.text().strip(),title=self.title_edit.text().strip(),
          status=self.status.currentText(),responsible=self.responsible.text().strip(),
          due_date=self.due.date().toPython(),details=self.details.toPlainText().strip(),
          file_path=self.file.text().strip(),updated_at=datetime.now())

class GenericPage(QWidget):
    def __init__(self,window,module,label):
        super().__init__();self.window=window;self.module=module;self.label=label
        layout=QVBoxLayout(self);head=QHBoxLayout();title=QLabel(label);title.setObjectName("PageTitle")
        head.addWidget(title);head.addStretch()
        for text,fn in [("Nuevo",self.add),("Editar",self.edit),("Eliminar",self.delete)]:
            b=QPushButton(text);b.clicked.connect(fn);head.addWidget(b)
        layout.addLayout(head);self.table=QTableWidget(0,6);self.table.setHorizontalHeaderLabels(
            ["Código","Registro","Estado","Responsable","Fecha límite","Archivo"])
        self.table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows);layout.addWidget(self.table)
    def refresh(self):
        with Session() as s:rows=s.scalars(select(ModuleRecord).where(ModuleRecord.module==self.module).order_by(ModuleRecord.due_date)).all()
        self.table.setRowCount(len(rows))
        for r,x in enumerate(rows):
            for c,v in enumerate((x.code,x.title,x.status,x.responsible,x.due_date,x.file_path)):
                it=cell(v);self.table.setItem(r,c,it)
                if c==0:it.setData(Qt.ItemDataRole.UserRole,x.id)
    def selected(self):
        r=self.table.currentRow();return self.table.item(r,0).data(Qt.ItemDataRole.UserRole) if r>=0 else None
    def add(self):
        with Session() as s:
            p=project(s)
            if not p:return self.window.configure_project()
            d=GenericDialog(self,title=self.label)
            if d.exec():
                x=ModuleRecord(project_id=p.id,module=self.module,**d.values());s.add(x);s.flush()
                audit(s,self.module,x.id,"crear",x.title);s.commit()
        self.window.refresh_all()
    def edit(self):
        rid=self.selected()
        if not rid:return
        with Session() as s:
            x=s.get(ModuleRecord,rid);d=GenericDialog(self,x,self.label)
            if d.exec():
                for k,v in d.values().items():setattr(x,k,v)
                audit(s,self.module,x.id,"actualizar",x.title);s.commit()
        self.window.refresh_all()
    def delete(self):
        rid=self.selected()
        if rid and QMessageBox.question(self,"Confirmar","¿Eliminar el registro?")==QMessageBox.StandardButton.Yes:
            with Session() as s:x=s.get(ModuleRecord,rid);audit(s,self.module,rid,"eliminar",x.title);s.delete(x);s.commit()
            self.window.refresh_all()

class AlertPage(QWidget):
    def __init__(self,window):
        super().__init__();self.window=window;layout=QVBoxLayout(self)
        title=QLabel("Alertas");title.setObjectName("PageTitle");layout.addWidget(title)
        self.table=QTableWidget(0,5);self.table.setHorizontalHeaderLabels(["Tipo","Código","Actividad","Fecha","Detalle"])
        self.table.horizontalHeader().setSectionResizeMode(2,QHeaderView.ResizeMode.Stretch);layout.addWidget(self.table)
    def refresh(self):
        alerts=[]
        with Session() as s:
            tasks=s.scalars(select(Task).order_by(Task.end_date)).all()
            for t in tasks:
                evidence=len(t.evidence)
                if t.end_date<date.today() and t.status!="Terminada":alerts.append(("Vencida",t.code,t.title,t.end_date,"Actividad no terminada"))
                elif date.today()<=t.end_date<=date.today()+timedelta(days=14) and t.status!="Terminada":
                    alerts.append(("Próxima",t.code,t.title,t.end_date,"Vence en los próximos 14 días"))
                if t.status=="Terminada" and t.evidence_required and not evidence:
                    alerts.append(("Sin evidencia",t.code,t.title,t.end_date,"No acredita cumplimiento"))
        self.table.setRowCount(len(alerts))
        for r,row in enumerate(alerts):
            for c,v in enumerate(row):self.table.setItem(r,c,cell(v))

class AuditPage(QWidget):
    def __init__(self,window):
        super().__init__();layout=QVBoxLayout(self);title=QLabel("Auditoría");title.setObjectName("PageTitle");layout.addWidget(title)
        self.table=QTableWidget(0,5);self.table.setHorizontalHeaderLabels(["Fecha","Entidad","ID","Acción","Detalle"])
        self.table.horizontalHeader().setSectionResizeMode(4,QHeaderView.ResizeMode.Stretch);layout.addWidget(self.table)
    def refresh(self):
        with Session() as s:rows=s.scalars(select(Audit).order_by(Audit.happened_at.desc()).limit(1000)).all()
        self.table.setRowCount(len(rows))
        for r,a in enumerate(rows):
            for c,v in enumerate((a.happened_at.strftime("%Y-%m-%d %H:%M"),a.entity,a.entity_id,a.action,a.detail)):
                self.table.setItem(r,c,cell(v))

class ReportsPage(QWidget):
    def __init__(self,window):
        super().__init__();self.window=window;layout=QVBoxLayout(self)
        title=QLabel("Informes y respaldos");title.setObjectName("PageTitle");layout.addWidget(title)
        info=QLabel(f"Los datos se guardan localmente en:\n{ROOT}");info.setWordWrap(True);layout.addWidget(info)
        for text,fn in [("Generar informe HTML de avance",self.html_report),
                        ("Exportar plan de trabajo a CSV",self.csv_report),
                        ("Crear respaldo completo ZIP",self.backup),
                        ("Abrir carpeta de datos",lambda:open_local(ROOT))]:
            b=QPushButton(text);b.setMinimumWidth(360);b.clicked.connect(fn);layout.addWidget(b,alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addStretch()
    def refresh(self):pass
    def csv_report(self):
        target=ROOT/"reportes"/f"plan_trabajo_{date.today().isoformat()}.csv"
        with Session() as s:rows=s.scalars(select(Task).order_by(Task.start_date,Task.code)).all()
        with target.open("w",encoding="utf-8-sig",newline="") as f:
            w=csv.writer(f);w.writerow(["fase","codigo","actividad","responsable","inicio","fin","estado","prioridad","avance","evidencias"])
            for t in rows:w.writerow([t.phase,t.code,t.title,t.responsible,t.start_date,t.end_date,t.status,t.priority,t.progress,len(t.evidence)])
        open_local(target)
    def html_report(self):
        target=ROOT/"reportes"/f"informe_avance_{date.today().isoformat()}.html"
        with Session() as s:
            p=project(s);tasks=s.scalars(select(Task).order_by(Task.start_date,Task.code)).all()
            ok=sum(t.status=="Terminada" and (not t.evidence_required or len(t.evidence)>0) for t in tasks)
        trs="".join("<tr>"+"".join(f"<td>{html.escape(str(v or ''))}</td>" for v in
            (t.phase,t.code,t.title,t.responsible,t.start_date,t.end_date,t.status,f"{t.progress}%",len(t.evidence)))+"</tr>" for t in tasks)
        name=html.escape(p.name if p else "Proyecto sin configurar");code=html.escape(p.code if p else "")
        pct=round(ok*100/len(tasks)) if tasks else 0
        doc=f"""<!doctype html><html lang="es"><meta charset="utf-8"><title>Informe</title>
        <style>body{{font-family:Arial;margin:36px;color:#25313c}}h1{{color:#17324d}}.kpi{{font-size:28px;color:#00796b}}
        table{{border-collapse:collapse;width:100%;font-size:12px}}th,td{{border:1px solid #ccd5dd;padding:7px}}
        th{{background:#17324d;color:#fff}}tr:nth-child(even){{background:#f4f6f8}}</style>
        <h1>{name}</h1><p>{code} · Informe generado el {date.today()}</p>
        <p class="kpi">{pct}% de cumplimiento acreditado</p>
        <p>Regla: actividad terminada + evidencia requerida = cumplimiento.</p>
        <table><tr><th>Fase</th><th>Código</th><th>Actividad</th><th>Responsable</th><th>Inicio</th>
        <th>Fin</th><th>Estado</th><th>Avance</th><th>Evidencias</th></tr>{trs}</table></html>"""
        target.write_text(doc,encoding="utf-8");open_local(target)
    def backup(self):
        target=ROOT/"respaldos"/f"respaldo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        with zipfile.ZipFile(target,"w",zipfile.ZIP_DEFLATED) as z:
            if DB_PATH.exists():z.write(DB_PATH,DB_PATH.name)
            for folder in ("evidencias","documentos"):
                for f in (ROOT/folder).rglob("*"):
                    if f.is_file():z.write(f,f.relative_to(ROOT))
        QMessageBox.information(self,"Respaldo",f"Respaldo creado:\n{target}");open_local(target)

class SettingsPage(QWidget):
    def __init__(self,window):
        super().__init__();self.window=window;layout=QVBoxLayout(self)
        title=QLabel("Configuración");title.setObjectName("PageTitle");layout.addWidget(title)
        self.summary=QLabel();self.summary.setWordWrap(True);layout.addWidget(self.summary)
        edit=QPushButton("Editar datos del proyecto");edit.clicked.connect(window.configure_project);layout.addWidget(edit,alignment=Qt.AlignmentFlag.AlignLeft)
        rule=QLabel("Regla de cumplimiento: una actividad terminada solo cuenta como cumplida cuando posee evidencia, salvo que se desactive expresamente la exigencia.")
        rule.setWordWrap(True);layout.addWidget(rule);layout.addStretch()
    def refresh(self):
        with Session() as s:p=project(s)
        self.summary.setText("Proyecto sin configurar" if not p else
          f"<b>{html.escape(p.name)}</b><br>Código: {html.escape(p.code)}<br>Territorio: {html.escape(p.location)}<br>"
          f"Responsable: {html.escape(p.principal_investigator)}<br>Periodo: {p.start_date} a {p.end_date}")

class ProjectPage(SettingsPage):
    pass

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__();self.setWindowTitle(APP_TITLE);self.resize(1420,860);self.setMinimumSize(1100,680)
        central=QWidget();self.setCentralWidget(central);outer=QVBoxLayout(central);outer.setContentsMargins(0,0,0,0)
        header=QFrame();header.setObjectName("Header");hl=QVBoxLayout(header)
        self.app_title=QLabel(APP_TITLE);self.app_title.setObjectName("AppTitle")
        self.app_subtitle=QLabel("Gestión local, trazable y respaldable");self.app_subtitle.setObjectName("Subtitle")
        hl.addWidget(self.app_title);hl.addWidget(self.app_subtitle);outer.addWidget(header)
        splitter=QSplitter();self.nav=QListWidget();self.nav.setFixedWidth(225);self.stack=QStackedWidget()
        splitter.addWidget(self.nav);splitter.addWidget(self.stack);splitter.setStretchFactor(1,1);outer.addWidget(splitter)
        self.pages=[]
        generic_labels={
          "documents":"Gestión documental","review":"Revisión sistemática","instruments":"Instrumentos",
          "fieldwork":"Trabajo de campo","analysis":"Análisis","workshop":"Taller participativo",
          "ahp":"Proceso Analítico Jerárquico (AHP)","indicators":"Indicadores","products":"Productos"}
        for label,key in MODULES:
            self.nav.addItem(QListWidgetItem(label))
            if key=="dashboard":page=DashboardPage(self)
            elif key=="projects":page=ProjectPage(self)
            elif key=="tasks":page=TaskPage(self)
            elif key=="gantt":page=GanttPage(self)
            elif key=="evidence":page=EvidencePage(self)
            elif key=="organizations":page=OrganizationPage(self)
            elif key=="reports":page=ReportsPage(self)
            elif key=="alerts":page=AlertPage(self)
            elif key=="audit":page=AuditPage(self)
            elif key=="settings":page=SettingsPage(self)
            else:page=GenericPage(self,key,generic_labels[key])
            self.pages.append(page);self.stack.addWidget(page)
        self.nav.currentRowChanged.connect(self.change_page);self.nav.setCurrentRow(0)
        with Session() as s:
            if not project(s):self.configure_project(first_run=True)
        self.refresh_all()
    def change_page(self,index):
        self.stack.setCurrentIndex(index);page=self.pages[index]
        if hasattr(page,"refresh"):page.refresh()
    def refresh_all(self):
        for page in self.pages:
            if hasattr(page,"refresh"):
                try:page.refresh()
                except Exception as e:print(f"Refresh: {e}",file=sys.stderr)
        with Session() as s:
            p=project(s)
            if p:self.app_title.setText(p.name);self.app_subtitle.setText(f"{p.code} · {p.location}")
    def configure_project(self,first_run=False):
        with Session() as s:
            p=project(s);d=ProjectDialog(self,p)
            if d.exec():
                if p:
                    for k,v in d.values().items():setattr(p,k,v)
                    audit(s,"project",p.id,"actualizar",p.name)
                else:
                    p=Project(**d.values());s.add(p);s.flush();audit(s,"project",p.id,"crear",p.name)
                s.commit();self.refresh_all()
            elif first_run:
                QMessageBox.information(self,"Configuración pendiente",
                    "Puede registrar el proyecto más adelante desde Configuración.")

STYLE = """
QWidget { font-family: 'Segoe UI'; font-size: 10pt; background: #f4f6f8; color: #263746; }
#Header { background: #17324d; min-height: 72px; }
#AppTitle { color: white; font-size: 18pt; font-weight: 700; }
#Subtitle { color: #d8e7f1; }
#PageTitle { font-size: 17pt; font-weight: 700; color: #17324d; padding: 4px; }
#Card { background: white; border: 1px solid #d8e0e7; border-radius: 7px; min-height: 95px; }
#CardValue { font-size: 22pt; font-weight: 700; color: #00796b; }
QListWidget { background: #203c56; color: white; border: 0; padding-top: 8px; }
QListWidget::item { padding: 9px 12px; }
QListWidget::item:selected { background: #2f668e; border-left: 4px solid #5fc4b8; }
QPushButton { background: #ffffff; border: 1px solid #b7c4cf; border-radius: 5px; padding: 7px 12px; }
QPushButton:hover { background: #e9f2f7; }
QTableWidget { background: white; alternate-background-color: #f5f8fa; border: 1px solid #d6dfe6; }
QHeaderView::section { background: #e6edf2; padding: 7px; border: 0; border-right: 1px solid #cbd5dc; font-weight: 600; }
QLineEdit, QComboBox, QDateEdit, QSpinBox, QTextEdit { background: white; border: 1px solid #b8c5cf; border-radius: 4px; padding: 5px; }
"""

def main():
    app=QApplication(sys.argv);app.setApplicationName(APP_TITLE);app.setStyleSheet(STYLE)
    win=MainWindow();win.show();sys.exit(app.exec())

if __name__=="__main__":
    main()
