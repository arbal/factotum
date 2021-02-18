from django.apps import apps
from django.conf import settings
from django.db import connection
from django.db import models


class AuditLog(models.Model):
    extracted_text = models.ForeignKey(
        "ExtractedText",
        to_field="data_document_id",
        related_name="auditlogs",
        on_delete=models.DO_NOTHING,
        null=True,
        db_constraint=False,
    )
    rawchem_id = models.PositiveIntegerField(null=True, db_index=True)
    object_key = models.PositiveIntegerField(null=True)
    model_name = models.CharField(max_length=128)
    field_name = models.CharField(max_length=128)
    old_value = models.TextField(null=True)
    new_value = models.TextField(null=True)
    date_created = models.DateTimeField(auto_now_add=True, db_index=True)
    action = models.CharField(max_length=1)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, blank=True, null=True, on_delete=models.SET_NULL
    )

    @classmethod
    def remove_trigger_sql(cls):
        default_db = settings.DATABASES["default"]["NAME"]
        sql_stmnt = (
            "SELECT Concat('DROP TRIGGER ', Trigger_Name, ';') "
            "FROM  information_schema.TRIGGERS "
            f"WHERE TRIGGER_SCHEMA = '{default_db}' AND "
            "TRIGGER_NAME LIKE '%auditlog_trigger';"
        )
        with connection.cursor() as cursor:
            cursor.execute(sql_stmnt)
            drop_stmnts = [c[0] for c in cursor.fetchall()]
            for s in drop_stmnts:
                cursor.execute(s)

    @classmethod
    def add_trigger_sql(cls):
        with connection.cursor() as cursor:
            cursor.execute(cls.get_trigger_sql())

    @classmethod
    def get_trigger_sql(cls):
        """Scans all models for auditlog_fields() methods, and builds SQL string defining audit log triggers

        Returns:
            string -- a valid SQL string that can be used in a migration operation
        """
        app_label = "dashboard"
        trigger_sql = ""
        auditlog_fields = {}

        # Build dictionary of auditable fields by model
        for model in apps.all_models[app_label]:
            try:
                fields = apps.get_model(app_label, model_name=model).auditlog_fields()
                if fields is not None:
                    auditlog_fields[model] = fields
            except AttributeError:
                pass

        # Build SQL trigger string by model and auditable fields
        for model in auditlog_fields:
            table_name = app_label + "_" + model
            id = apps.get_model(app_label, model_name=model)._meta.pk.attname
            rawchem_audit_field = cls.get_extracted_text_audit_field(model, False)
            rawchem_audit_field_insert = cls.get_extracted_text_audit_field(model, True)
            rawchem_field = "chem_id" if model == "functionaluse" else id

            trigger_sql += f"""
                CREATE TRIGGER  {table_name}_update_auditlog_trigger
                AFTER UPDATE ON {table_name}
                FOR EACH ROW
                BEGIN
            """
            for field in auditlog_fields[model]:
                trigger_sql += f"""
                    IF IFNULL(NEW.{field}, '') <> IFNULL(OLD.{field}, '') THEN
                        insert into dashboard_auditlog (extracted_text_id, rawchem_id,
                            object_key, model_name, field_name, date_created, 
                            old_value, new_value, action, user_id)
                        values ({rawchem_audit_field}, NEW.{rawchem_field},
                            NEW.{id}, '{model}', '{field}', now(),
                            OLD.{field}, NEW.{field}, 'U', @current_user);
                    END IF;
                """
            trigger_sql += f"""
                END;

                CREATE TRIGGER  {table_name}_insert_auditlog_trigger
                AFTER INSERT ON {table_name}
                FOR EACH ROW
                BEGIN
            """
            for field in auditlog_fields[model]:
                trigger_sql += f"""
                    IF IFNULL(NEW.{field}, '') <> '' THEN
                        insert into dashboard_auditlog (extracted_text_id, rawchem_id,
                            object_key, model_name, field_name, date_created,
                            old_value, new_value, action, user_id)
                        values ({rawchem_audit_field_insert}, NEW.{rawchem_field},
                            NEW.{id}, '{model}', '{field}', now(),
                            null, NEW.{field}, 'I', @current_user);
                    END IF;
                """
            trigger_sql += f"""
                END;

                CREATE TRIGGER  {table_name}_delete_auditlog_trigger
                AFTER DELETE ON {table_name}
                FOR EACH ROW
                BEGIN
            """
            for field in auditlog_fields[model]:
                trigger_sql += f"""
                    IF IFNULL(OLD.{field}, '') <> '' THEN
                        insert into dashboard_auditlog (extracted_text_id, rawchem_id,
                            object_key, model_name, field_name, date_created,
                            old_value, new_value, action, user_id)
                        values ({rawchem_audit_field}, OLD.{rawchem_field},
                            OLD.{id}, '{model}', '{field}', now(),
                            OLD.{field}, null, 'D', @current_user);
                    END IF;
                """
            trigger_sql += f"""
                END;
            """
        return trigger_sql

    @classmethod
    def get_extracted_text_audit_field(cls, model, insert):
        prefix = "NEW" if insert else "OLD"

        if model == "rawchem":
            return f"{prefix}.extracted_text_id"

        if model == "functionaluse":
            rawchem_join_field = "chem_id"
        else:
            rawchem_join_field = "rawchem_ptr_id"

        return f"(select extracted_text_id from dashboard_rawchem where id = {prefix}.{rawchem_join_field})"

    def verbose(self):
        return "%s.%s:%s | %s --> %s" % (
            self.model_name,
            self.object_key,
            self.field_name,
            self.old_value,
            self.new_value,
        )
