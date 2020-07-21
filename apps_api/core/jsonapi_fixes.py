import copy

from django.db.models import Manager

from rest_framework import relations
from rest_framework.exceptions import ParseError
from rest_framework.serializers import BaseSerializer, ListSerializer, Serializer
from rest_framework.settings import api_settings
from rest_framework_json_api import utils
from rest_framework_json_api.renderers import JSONRenderer as BaseJSONRenderer
from rest_framework_json_api.relations import ResourceRelatedField
from rest_framework_json_api.serializers import ModelSerializer as BaseModelSerializer
from rest_framework_json_api.utils import (
    get_included_serializers,
    get_included_resources,
)


class IncludedResourcesValidationMixin(object):
    """This mixin is the exact same as DRF:JA's with the exception of

            this_field_name = inflection.underscore(field_path[0])

    being replaced with

            this_field_name = field_path[0]

    Otherwise validation would not pass.
    """

    def __init__(self, *args, **kwargs):
        context = kwargs.get("context")
        request = context.get("request") if context else None
        view = context.get("view") if context else None

        def validate_path(serializer_class, field_path, path):
            serializers = get_included_serializers(serializer_class)
            if serializers is None:
                raise ParseError("This endpoint does not support the include parameter")
            # This is the replaced line
            this_field_name = field_path[0]
            this_included_serializer = serializers.get(this_field_name)
            if this_included_serializer is None:
                raise ParseError(
                    "This endpoint does not support the include parameter for path {}".format(
                        path
                    )
                )
            if len(field_path) > 1:
                new_included_field_path = field_path[1:]
                # We go down one level in the path
                validate_path(this_included_serializer, new_included_field_path, path)

        if request and view:
            included_resources = get_included_resources(request)
            for included_field_name in included_resources:
                included_field_path = included_field_name.split(".")
                this_serializer_class = view.get_serializer_class()
                # lets validate the current path
                validate_path(
                    this_serializer_class, included_field_path, included_field_name
                )

        super(IncludedResourcesValidationMixin, self).__init__(*args, **kwargs)


class ModelSerializer(IncludedResourcesValidationMixin, BaseModelSerializer):
    """This is an implementation that uses the custom IncludedResourcesValidationMixin
    """

    pass


class JSONRenderer(BaseJSONRenderer):
    """This is the exact same as the JSONRenderer from rest_framework_json_api.renderers
    without the mandate that included resources need to be snake_case.  When DRF:JA
    pulls the include parameters it uses

            included_resources = [inflection.underscore(value) for value in included_resources]

    This breaks quite a bit of functionality in our case as we have opted to use camelCase.
    The offending line has been replace with

            included_resources = [value for value in included_resources]

    """

    @classmethod
    def extract_included(
        cls, fields, resource, resource_instance, included_resources, included_cache
    ):
        """
        Adds related data to the top level included key when the request includes
        ?include=example,example_field2
        """
        # this function may be called with an empty record (example: Browsable Interface)
        if not resource_instance:
            return

        current_serializer = fields.serializer
        context = current_serializer.context
        included_serializers = utils.get_included_serializers(current_serializer)
        included_resources = copy.copy(included_resources)
        # This is the replaced line
        included_resources = [value for value in included_resources]

        for field_name, field in iter(fields.items()):
            # Skip URL field
            if field_name == api_settings.URL_FIELD_NAME:
                continue

            # Skip fields without relations or serialized data
            if not isinstance(
                field,
                (relations.RelatedField, relations.ManyRelatedField, BaseSerializer),
            ):
                continue

            try:
                included_resources.remove(field_name)
            except ValueError:
                # Skip fields not in requested included resources
                # If no child field, directly continue with the next field
                if field_name not in [
                    node.split(".")[0] for node in included_resources
                ]:
                    continue

            relation_instance = cls.extract_relation_instance(field, resource_instance)
            if isinstance(relation_instance, Manager):
                relation_instance = relation_instance.all()

            serializer_data = resource.get(field_name)

            if isinstance(field, relations.ManyRelatedField):
                serializer_class = included_serializers[field_name]
                field = serializer_class(relation_instance, many=True, context=context)
                serializer_data = field.data

            if isinstance(field, relations.RelatedField):
                if relation_instance is None or not serializer_data:
                    continue

                many = field._kwargs.get("child_relation", None) is not None

                if isinstance(field, ResourceRelatedField) and not many:
                    already_included = (
                        serializer_data["type"] in included_cache
                        and serializer_data["id"]
                        in included_cache[serializer_data["type"]]
                    )

                    if already_included:
                        continue

                serializer_class = included_serializers[field_name]
                field = serializer_class(relation_instance, many=many, context=context)
                serializer_data = field.data

            new_included_resources = [
                key.replace("%s." % field_name, "", 1)
                for key in included_resources
                if field_name == key.split(".")[0]
            ]

            if isinstance(field, ListSerializer):
                serializer = field.child
                relation_type = utils.get_resource_type_from_serializer(serializer)
                relation_queryset = list(relation_instance)

                if serializer_data:
                    for position in range(len(serializer_data)):
                        serializer_resource = serializer_data[position]
                        nested_resource_instance = relation_queryset[position]
                        resource_type = (
                            relation_type
                            or utils.get_resource_type_from_instance(
                                nested_resource_instance
                            )
                        )
                        serializer_fields = utils.get_serializer_fields(
                            serializer.__class__(
                                nested_resource_instance, context=serializer.context
                            )
                        )
                        new_item = cls.build_json_resource_obj(
                            serializer_fields,
                            serializer_resource,
                            nested_resource_instance,
                            resource_type,
                            getattr(serializer, "_poly_force_type_resolution", False),
                        )
                        included_cache[new_item["type"]][
                            new_item["id"]
                        ] = utils.format_field_names(new_item)
                        cls.extract_included(
                            serializer_fields,
                            serializer_resource,
                            nested_resource_instance,
                            new_included_resources,
                            included_cache,
                        )

            if isinstance(field, Serializer):
                relation_type = utils.get_resource_type_from_serializer(field)

                # Get the serializer fields
                serializer_fields = utils.get_serializer_fields(field)
                if serializer_data:
                    new_item = cls.build_json_resource_obj(
                        serializer_fields,
                        serializer_data,
                        relation_instance,
                        relation_type,
                        getattr(field, "_poly_force_type_resolution", False),
                    )
                    included_cache[new_item["type"]][
                        new_item["id"]
                    ] = utils.format_field_names(new_item)
                    cls.extract_included(
                        serializer_fields,
                        serializer_data,
                        relation_instance,
                        new_included_resources,
                        included_cache,
                    )
