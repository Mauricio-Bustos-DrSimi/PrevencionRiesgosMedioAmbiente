import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="Obligacion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("creada_en", models.DateTimeField(auto_now_add=True)),
            ],
            options={"verbose_name": "obligación", "verbose_name_plural": "obligaciones"},
        ),
        migrations.CreateModel(
            name="VersionObligacion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("numero", models.PositiveIntegerField()),
                ("nombre", models.CharField(max_length=255)),
                ("norma_origen", models.CharField(max_length=255, verbose_name="norma de origen")),
                ("titular", models.CharField(choices=[("centro_costo", "Centro de costo"), ("trabajador", "Trabajador"), ("externo", "Externo"), ("empresa", "Empresa")], max_length=30)),
                ("periodicidad", models.CharField(choices=[("anual", "Anual"), ("bienal", "Bienal"), ("por_evento", "Por evento"), ("permanente", "Permanente")], max_length=30)),
                ("tipo_version", models.CharField(choices=[("alta", "Alta"), ("correccion", "Corrección"), ("cierre", "Cierre")], max_length=20)),
                ("fecha_cierre", models.DateField(blank=True, null=True)),
                ("motivo", models.TextField()),
                ("creada_en", models.DateTimeField(auto_now_add=True)),
                ("autor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="versiones_obligacion_creadas", to=settings.AUTH_USER_MODEL)),
                ("obligacion", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="versiones", to="obligaciones.obligacion")),
            ],
            options={"verbose_name": "versión de obligación", "verbose_name_plural": "versiones de obligación", "ordering": ("numero",)},
        ),
        migrations.AddConstraint(
            model_name="versionobligacion",
            constraint=models.UniqueConstraint(fields=("obligacion", "numero"), name="obligacion_numero_version_unico"),
        ),
    ]
