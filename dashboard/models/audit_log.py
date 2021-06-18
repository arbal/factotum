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

    def __str__(self):
        return f"{self.old_value} -> {self.new_value}, {self.action} on {self.model_name}|{self.field_name}"

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
            sql = cls.get_trigger_sql()
            cursor.execute(sql)
            # functional use related audit logs are different, handle with explict sql
            sql = cls.get_functional_use_trigger_sql()
            cursor.execute(sql)

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
                if fields is not None and len(fields) > 0:
                    auditlog_fields[model] = fields
            except AttributeError:
                pass

        # Build SQL trigger string by model and auditable fields
        for model in auditlog_fields:
            table_name = app_label + "_" + model
            id = apps.get_model(app_label, model_name=model)._meta.pk.attname
            rawchem_audit_field = cls.get_extracted_text_audit_field(model, False)
            rawchem_audit_field_insert = cls.get_extracted_text_audit_field(model, True)

            trigger_sql += f"""
                CREATE TRIGGER  {table_name}_update_auditlog_trigger
                AFTER UPDATE ON {table_name}
                FOR EACH ROW
                BEGIN
            """
            for field in auditlog_fields[model]:
                if model == "rawchem" and field == "dsstox_id":
                    # audit sid
                    trigger_sql += f"""
                    IF IFNULL(NEW.{field}, '') <> IFNULL(OLD.{field}, '') THEN
                        insert into dashboard_auditlog (extracted_text_id, rawchem_id,
                            object_key, model_name, field_name, date_created, 
                            old_value, new_value, action, user_id)
                        values ({rawchem_audit_field}, NEW.{id}, NEW.{id}, '{model}', 'sid', now(),
                            if(OLD.{field} is null,null,(select sid from dashboard_dsstoxlookup where id=OLD.{field})),
                            if(NEW.{field} is null,null,(select sid from dashboard_dsstoxlookup where id=NEW.{field})), 
                            'U', @current_user);
                    END IF;
                    """
                else:
                    trigger_sql += f"""
                    IF IFNULL(NEW.{field}, '') <> IFNULL(OLD.{field}, '') THEN
                        insert into dashboard_auditlog (extracted_text_id, rawchem_id,
                            object_key, model_name, field_name, date_created, 
                            old_value, new_value, action, user_id)
                        values ({rawchem_audit_field}, NEW.{id},
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
                if model == "rawchem" and field == "dsstox_id":
                    # audit sid
                    trigger_sql += f"""
                    IF IFNULL(NEW.{field}, '') <> '' THEN
                        insert into dashboard_auditlog (extracted_text_id, rawchem_id,
                            object_key, model_name, field_name, date_created,
                            old_value, new_value, action, user_id)
                        values ({rawchem_audit_field_insert}, NEW.{id},
                            NEW.{id}, '{model}', 'sid', now(), null,
                            (select sid from dashboard_dsstoxlookup where id=NEW.{field}), 'I', @current_user);
                    END IF;
                    """
                else:
                    trigger_sql += f"""
                    IF IFNULL(NEW.{field}, '') <> '' THEN
                        insert into dashboard_auditlog (extracted_text_id, rawchem_id,
                            object_key, model_name, field_name, date_created,
                            old_value, new_value, action, user_id)
                        values ({rawchem_audit_field_insert}, NEW.{id},
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
                if model == "rawchem" and field == "dsstox_id":
                    # audit sid
                    trigger_sql += f"""
                    IF IFNULL(OLD.{field}, '') <> '' THEN
                        insert into dashboard_auditlog (extracted_text_id, rawchem_id,
                            object_key, model_name, field_name, date_created,
                            old_value, new_value, action, user_id)
                        values ({rawchem_audit_field}, OLD.{id},
                            OLD.{id}, '{model}', 'sid', now(),
                            (select sid from dashboard_dsstoxlookup where id=OLD.{field}), null, 'D', @current_user);
                    END IF;
                    """
                else:
                    trigger_sql += f"""
                    IF IFNULL(OLD.{field}, '') <> '' THEN
                        insert into dashboard_auditlog (extracted_text_id, rawchem_id,
                            object_key, model_name, field_name, date_created,
                            old_value, new_value, action, user_id)
                        values ({rawchem_audit_field}, OLD.{id},
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

        rawchem_join_field = "rawchem_ptr_id"
        return f"(select extracted_text_id from dashboard_rawchem where id = {prefix}.{rawchem_join_field})"

    @classmethod
    def get_functional_use_trigger_sql(cls):
        return """
        CREATE TRIGGER  dashboard_functionalusetorawchem_update_auditlog_trigger
        AFTER UPDATE ON dashboard_functionalusetorawchem
        FOR EACH ROW
        BEGIN
            declare old_cat_id int(11);
            declare new_cat_id int(11);
            declare old_harmonized varchar(50) DEFAULT '';
            declare new_harmonized varchar(50) DEFAULT '';
            IF IFNULL(NEW.functional_use_id, '') <> IFNULL(OLD.functional_use_id, '') THEN
                insert into dashboard_auditlog (extracted_text_id, rawchem_id,
                        object_key, model_name, field_name, date_created, 
                        old_value, new_value, action, user_id)
                values ((select extracted_text_id from dashboard_rawchem where id = OLD.chemical_id), NEW.chemical_id,
                        NEW.id, 'functionalusetorawchem', 'report_funcuse', now(),
                        (select report_funcuse from dashboard_functionaluse where id = OLD.functional_use_id), 
                        (select report_funcuse from dashboard_functionaluse where id = NEW.functional_use_id), 
                        'U', @current_user);
                            
                select category_id into old_cat_id from dashboard_functionaluse where id = OLD.functional_use_id;
                IF old_cat_id is not null THEN
                    select fuc.title into old_harmonized from dashboard_functionalusecategory fuc where id = old_cat_id;
                END IF;    
                select category_id into new_cat_id from dashboard_functionaluse where id = NEW.functional_use_id;
                IF new_cat_id is not null THEN
                    select fuc.title into new_harmonized from dashboard_functionalusecategory fuc where id = new_cat_id;
                END IF;
                
                IF IFNULL(old_harmonized, '') <> IFNULL(new_harmonized, '') THEN
                    insert into dashboard_auditlog (extracted_text_id, rawchem_id,
                        object_key, model_name, field_name, date_created, 
                        old_value, new_value, action, user_id)
                    values ((select extracted_text_id from dashboard_rawchem where id = OLD.chemical_id), NEW.chemical_id,
                            NEW.id, 'functionalusetorawchem', 'harmonized category', now(), 
                            old_harmonized, new_harmonized, 'U', @current_user);
                END IF;
            END IF;
        END;
        
        
        CREATE TRIGGER  dashboard_functionalusetorawchem_insert_auditlog_trigger
        AFTER INSERT ON dashboard_functionalusetorawchem
        FOR EACH ROW
        BEGIN
            declare new_cat_id int(11);
            declare new_harmonized varchar(50);

            insert into dashboard_auditlog (extracted_text_id, rawchem_id,
                    object_key, model_name, field_name, date_created,
                    old_value, new_value, action, user_id)
            values ((select extracted_text_id from dashboard_rawchem where id = NEW.chemical_id), NEW.chemical_id,
                    NEW.id, 'functionalusetorawchem', 'report_funcuse', now(),
                    null, (select report_funcuse from dashboard_functionaluse where id = NEW.functional_use_id),
                    'I', @current_user);

            select category_id into new_cat_id from dashboard_functionaluse where id = NEW.functional_use_id;
            IF new_cat_id is not null THEN
                select fuc.title into new_harmonized from dashboard_functionalusecategory fuc where id = new_cat_id;
            END IF;
                        
            IF IFNULL(new_harmonized, '') <> '' THEN
                insert into dashboard_auditlog (extracted_text_id, rawchem_id,
                        object_key, model_name, field_name, date_created, 
                        old_value, new_value, action, user_id)
                values ((select extracted_text_id from dashboard_rawchem where id = NEW.chemical_id), NEW.chemical_id,
                        NEW.id, 'functionalusetorawchem', 'harmonized category', now(), 
                        null, new_harmonized, 'I', @current_user);
            END IF;
        END;
        
        CREATE TRIGGER  dashboard_functionalusetorawchem_delete_auditlog_trigger
        AFTER DELETE ON dashboard_functionalusetorawchem
        FOR EACH ROW
        BEGIN
            declare old_cat_id int(11);
            declare old_harmonized varchar(50);
                    
            insert into dashboard_auditlog (extracted_text_id, rawchem_id,
                    object_key, model_name, field_name, date_created,
                    old_value, new_value, action, user_id)
            values ((select extracted_text_id from dashboard_rawchem where id = OLD.chemical_id), OLD.chemical_id,
                    OLD.id, 'functionalusetorawchem', 'report_funcuse', now(),
                    (select report_funcuse from dashboard_functionaluse where id = OLD.functional_use_id), null, 
                    'D', @current_user);

            select category_id into old_cat_id from dashboard_functionaluse where id = OLD.functional_use_id;
            IF old_cat_id is not null THEN
                select fuc.title into old_harmonized from dashboard_functionalusecategory fuc where id = old_cat_id;
            END IF;     
            IF IFNULL(old_harmonized, '') <> '' THEN
                insert into dashboard_auditlog (extracted_text_id, rawchem_id,
                        object_key, model_name, field_name, date_created, 
                        old_value, new_value, action, user_id)
                values ((select extracted_text_id from dashboard_rawchem where id = OLD.chemical_id), OLD.chemical_id,
                        OLD.id, 'functionalusetorawchem', 'harmonized category', now(), old_harmonized, null,
                        'D', @current_user);
            END IF;
        END;
                
                
        CREATE TRIGGER  dashboard_functionaluse_update_auditlog_trigger
        AFTER UPDATE ON dashboard_functionaluse
        FOR EACH ROW
        BEGIN
            IF IFNULL(NEW.report_funcuse, '') <> IFNULL(OLD.report_funcuse, '') THEN
                insert into dashboard_auditlog (extracted_text_id, rawchem_id,
                        object_key, model_name, field_name, date_created, 
                        old_value, new_value, action, user_id)
                select rc.extracted_text_id,furc.chemical_id, 
                        fu.id, 'functionaluse', 'report_funcuse', now(), 
                        OLD.report_funcuse, NEW.report_funcuse, 'U', @current_user
                from dashboard_functionaluse fu
                join dashboard_functionalusetorawchem furc on fu.id = furc.functional_use_id
                join dashboard_rawchem rc on furc.chemical_id = rc.id
                where fu.id = NEW.id;
            END IF;
            
            IF IFNULL(NEW.category_id, '') <> IFNULL(OLD.category_id, '') THEN
                insert into dashboard_auditlog (extracted_text_id, rawchem_id,
                        object_key, model_name, field_name, date_created, 
                        old_value, new_value, action, user_id)
                select rc.extracted_text_id, furc.chemical_id, 
                        fu.id, 'functionaluse', 'harmonized category', now(), 
                    if(OLD.category_id is null, null, (select title from dashboard_functionalusecategory where id=OLD.category_id)),
                    if(NEW.category_id is null, null, (select title from dashboard_functionalusecategory where id=NEW.category_id)),  
                    'U', @current_user
                from dashboard_functionaluse fu
                join dashboard_functionalusetorawchem furc on fu.id = furc.functional_use_id
                join dashboard_rawchem rc on furc.chemical_id = rc.id
                where fu.id = NEW.id;
            END IF;
        END;
        
        
        CREATE TRIGGER  dashboard_functionalusecategory_update_auditlog_trigger
        AFTER UPDATE ON dashboard_functionalusecategory
        FOR EACH ROW
        BEGIN
            IF IFNULL(NEW.title, '') <> IFNULL(OLD.title, '') THEN
                insert into dashboard_auditlog (extracted_text_id, rawchem_id,
                        object_key, model_name, field_name, date_created, 
                        old_value, new_value, action, user_id)
                select rc.extracted_text_id, furc.chemical_id, 
                        fuc.id, 'functionalusecategory', 'harmonized category', now(), 
                        OLD.title, NEW.title, 'U', @current_user
                from dashboard_functionalusecategory fuc
                join dashboard_functionaluse fu on fuc.id = fu.category_id
                join dashboard_functionalusetorawchem furc on fu.id = furc.functional_use_id
                join dashboard_rawchem rc on furc.chemical_id = rc.id
                where fuc.id = NEW.id;
            END IF;
        END;
        """

    def verbose(self):
        return "%s.%s:%s | %s --> %s" % (
            self.model_name,
            self.object_key,
            self.field_name,
            self.old_value,
            self.new_value,
        )
