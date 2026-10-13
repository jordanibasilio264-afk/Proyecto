"""
Ubicación: apps/usuarios/models.py
En settings.py (antes de la primera migración):
    AUTH_USER_MODEL = "usuarios.Usuario"
"""
from datetime import date, timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Count, Q
from django.utils import timezone

from .base import ModeloBase


class UsuarioManager(BaseUserManager):
    """Manager necesario porque el login es por email y no hay username."""

    use_in_migrations = True

    def _crear(self, email, password, **extra):
        if not email:
            raise ValueError("El correo electrónico es obligatorio.")
        email = self.normalize_email(email)  # solo normaliza el dominio; respeta mayúsculas del usuario
        usuario = self.model(email=email, **extra)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._crear(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("rol", "ADMIN")  # un superusuario siempre es admin
        if not extra["is_staff"] or not extra["is_superuser"]:
            raise ValueError("El superusuario debe tener is_staff e is_superuser en True.")
        return self._crear(email, password, **extra)


# Permisos por rol (códigos 'modulo.accion').
# Reglas del PDF: solo MEDICO diagnostica/receta; nadie elimina expedientes;
# auditoría es solo lectura.
PERMISOS_POR_ROL = {
    "ADMIN": {
        "usuarios.ver", "usuarios.crear", "usuarios.editar", "usuarios.eliminar",
        "usuarios.activar", "usuarios.asignar_roles",
        "pacientes.ver", "pacientes.crear", "pacientes.editar", "pacientes.eliminar",
        "medicos.ver", "medicos.crear", "medicos.editar", "medicos.eliminar",
        "citas.ver", "citas.crear", "citas.editar", "citas.confirmar",
        "citas.cancelar", "citas.reprogramar",
        "consultas.ver", "expedientes.ver", "recetas.ver",
        "medicamentos.ver", "medicamentos.crear", "medicamentos.editar",
        "medicamentos.eliminar",
        "pagos.ver", "pagos.crear", "pagos.generar_recibo", "pagos.ver_ingresos",
        "seguros.ver", "seguros.crear", "seguros.editar",
        "documentos.ver", "documentos.subir", "documentos.eliminar",
        "notificaciones.ver", "notificaciones.enviar",
        "dashboard.ver", "reportes.ver", "reportes.exportar",
        "auditoria.ver", "configuracion.ver", "configuracion.editar",
    },
    "MEDICO": {
        "pacientes.ver", "medicos.ver",
        "citas.ver", "citas.editar", "citas.confirmar",
        "consultas.ver", "consultas.crear", "consultas.editar",
        "expedientes.ver", "expedientes.crear", "expedientes.editar",
        "expedientes.descargar_pdf",
        "recetas.ver", "recetas.crear", "recetas.editar", "recetas.imprimir",
        "medicamentos.ver",
        "documentos.ver", "documentos.subir",
        "notificaciones.ver", "dashboard.ver",
        "reportes.ver", "reportes.exportar",
    },
    "RECEPCIONISTA": {
        "pacientes.ver", "pacientes.crear", "pacientes.editar",
        "medicos.ver",
        "citas.ver", "citas.crear", "citas.editar", "citas.confirmar",
        "citas.cancelar", "citas.reprogramar",
        "seguros.ver", "seguros.crear", "seguros.editar",
        "documentos.ver", "documentos.subir",
        "pagos.ver", "pagos.crear", "pagos.generar_recibo",
        "notificaciones.ver", "notificaciones.enviar",
        "dashboard.ver",
    },
    # Solo ve lo suyo: filtra por paciente=request.user en las vistas.
    "PACIENTE": {
        "pagos.ver","recetas.ver", "recetas.imprimir",
        "notificaciones.ver","configuracion.ver", 
    },
}


class Usuarios (AbstractUser):
    class Roles(models.TextChoices):
        ADMIN = "ADMIN", "Administrador"
        MEDICO = "MEDICO", "Médico"
        RECEPCIONISTA = "RECEPCIONISTA", "Recepcionista"
        PACIENTE = "PACIENTE", "Paciente"

    username = None  # el login es por email
    email = models.EmailField("correo electrónico", unique=True)
    rol = models.CharField(
        max_length=20, choices=Roles.choices, default=Roles.PACIENTE, db_index=True
    )
    telefono = models.CharField(max_length=20, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = UsuarioManager()

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        ordering = ["first_name", "last_name"]

    def __str__(self):
        return f"{self.get_full_name() or self.email} ({self.get_rol_display()})"

    # --- Roles y permisos ---------------------------------------------
    @property
    def es_admin(self):
        return self.rol == self.Roles.ADMIN

    @property
    def es_medico(self):
        return self.rol == self.Roles.MEDICO

    @property
    def es_recepcionista(self):
        return self.rol == self.Roles.RECEPCIONISTA

    @property
    def es_paciente(self):
        return self.rol == self.Roles.PACIENTE

    def tiene_permiso(self, codigo):
        """True si está activo y su rol incluye el permiso."""
        if not self.is_active:
            return False
        if self.is_superuser:
            return True
        return codigo in PERMISOS_POR_ROL.get(self.rol, set())


# =========================================================================
# Perfiles clínicos
# =========================================================================
class Especialidad(ModeloBase):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.CharField(max_length=255, blank=True)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "especialidad"
        verbose_name_plural = "especialidades"

    def __str__(self):
        return self.nombre


class Medico(ModeloBase):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="perfil_medico",
        limit_choices_to={"rol": "MEDICO"},
    )
    especialidades = models.ManyToManyField(
        Especialidad, related_name="medicos", blank=True
    )
    exequatur = models.CharField(
        "exequátur / No. de colegiatura", max_length=30, unique=True, null=True, blank=True
    )
    cedula = models.CharField(max_length=20, blank=True)
    consultorio = models.CharField("consultorio / sala", max_length=50, blank=True)
    duracion_cita_minutos = models.PositiveSmallIntegerField(default=30)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["usuario__first_name", "usuario__last_name"]
        verbose_name = "médico"
        verbose_name_plural = "médicos"

    def __str__(self):
        return f"Dr(a). {self.nombre_completo}"

    @property
    def nombre_completo(self):
        return self.usuario.get_full_name() or self.usuario.email

    def clean(self):
        if self.usuario_id and self.usuario.rol != Usuarios.Roles.MEDICO:
            raise ValidationError({"usuario": "El usuario debe tener rol Médico."})


class HorarioMedico(ModeloBase):
    """Horario de atención por día de la semana (RF-04)."""

    class Dia(models.IntegerChoices):
        LUNES = 0, "Lunes"
        MARTES = 1, "Martes"
        MIERCOLES = 2, "Miércoles"
        JUEVES = 3, "Jueves"
        VIERNES = 4, "Viernes"
        SABADO = 5, "Sábado"
        DOMINGO = 6, "Domingo"

    medico = models.ForeignKey(Medico, on_delete=models.CASCADE, related_name="horarios")
    dia_semana = models.PositiveSmallIntegerField(choices=Dia.choices)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["medico", "dia_semana", "hora_inicio"]
        verbose_name = "horario de médico"
        verbose_name_plural = "horarios de médicos"

    def __str__(self):
        return f"{self.medico} - {self.get_dia_semana_display()} {self.hora_inicio:%H:%M}-{self.hora_fin:%H:%M}"

    def clean(self):
        if self.hora_inicio and self.hora_fin:
            if self.hora_fin <= self.hora_inicio:
                raise ValidationError("La hora de fin debe ser posterior a la de inicio.")
            if self.medico_id:
                choque = HorarioMedico.objects.filter(
                    medico_id=self.medico_id,
                    dia_semana=self.dia_semana,
                    activo=True,
                    hora_inicio__lt=self.hora_fin,
                    hora_fin__gt=self.hora_inicio,
                ).exclude(pk=self.pk)
                if choque.exists():
                    raise ValidationError("Este horario se cruza con otro del mismo día.")


class PacienteQuerySet(models.QuerySet):
    def frecuentes(self, min_citas=5, dias=365):
        """RF-20: pacientes con al menos N citas atendidas en el período."""
        desde = timezone.now() - timedelta(days=dias)
        return self.annotate(
            total_atendidas=Count(
                "citas", filter=Q(citas__estado="ATENDIDA", citas__inicio__gte=desde)
            )
        ).filter(total_atendidas__gte=min_citas)


class Paciente(ModeloBase):
    class Sexo(models.TextChoices):
        MASCULINO = "M", "Masculino"
        FEMENINO = "F", "Femenino"
        OTRO = "O", "Otro"

    class TipoSangre(models.TextChoices):
        A_POS = "A+", "A+"
        A_NEG = "A-", "A-"
        B_POS = "B+", "B+"
        B_NEG = "B-", "B-"
        AB_POS = "AB+", "AB+"
        AB_NEG = "AB-", "AB-"
        O_POS = "O+", "O+"
        O_NEG = "O-", "O-"

    # Cuenta opcional: solo si el paciente usa el portal.
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="perfil_paciente",
        limit_choices_to={"rol": "PACIENTE"},
    )
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    cedula = models.CharField("cédula", max_length=20, unique=True, null=True, blank=True)
    fecha_nacimiento = models.DateField()
    sexo = models.CharField(max_length=1, choices=Sexo.choices)
    telefono = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    direccion = models.CharField(max_length=255, blank=True)
    tipo_sangre = models.CharField(max_length=3, choices=TipoSangre.choices, blank=True)
    contacto_emergencia_nombre = models.CharField(max_length=120, blank=True)
    contacto_emergencia_telefono = models.CharField(max_length=20, blank=True)
    activo = models.BooleanField(default=True)

    objects = PacienteQuerySet.as_manager()

    class Meta:
        ordering = ["apellidos", "nombres"]
        indexes = [models.Index(fields=["apellidos", "nombres"])]
        verbose_name = "paciente"
        verbose_name_plural = "pacientes"

    def __str__(self):
        return self.nombre_completo

    @property
    def nombre_completo(self):
        return f"{self.nombres} {self.apellidos}".strip()

    @property
    def edad(self):
        hoy = date.today()
        n = self.fecha_nacimiento
        return hoy.year - n.year - ((hoy.month, hoy.day) < (n.month, n.day))

    def clean(self):
        if self.usuario_id and self.usuario.rol != Usuarios.Roles.PACIENTE:
            raise ValidationError({"usuario": "El usuario debe tener rol Paciente."})