from drf_yasg import generators, openapi, utils
from drf_yasg.inspectors.field import get_basic_type_info
import uritemplate


class StandardSchemaGenerator(generators.OpenAPISchemaGenerator):
    def get_path_parameters(self, path, view_cls):
        # Get from serializer, not model
        parameters = []
        for variable in sorted(uritemplate.variables(path)):
            if view_cls.serializer_class:
                serializer = view_cls.serializer_class()
                serializer_field = serializer.fields[variable]
                attrs = get_basic_type_info(serializer_field) or {
                    "type": openapi.TYPE_STRING
                }
                description = getattr(serializer_field, "help_text")
                title = getattr(serializer_field, "label")
                field = openapi.Parameter(
                    name=variable,
                    title=utils.force_real_str(title),
                    description=utils.force_real_str(description),
                    required=True,
                    in_=openapi.IN_PATH,
                    **attrs,
                )
                parameters.append(field)
        return parameters
