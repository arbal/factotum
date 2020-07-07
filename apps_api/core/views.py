import datetime

from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.response import Response
from rest_framework_json_api.parsers import JSONParser


class ObtainExpiringAuthToken(ObtainAuthToken):
    parser_classes = [JSONParser]
    resource_name = "token"

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            token, created = Token.objects.get_or_create(
                user=serializer.validated_data["user"]
            )

            # Refresh existing tokens
            if not created:
                token.delete()
                token = Token.objects.create(user=serializer.validated_data["user"])
                token.created = datetime.datetime.utcnow()
                token.save()

            response_data = {"token": token.key}
            return Response(response_data, content_type="application/vnd.api+json")

        return Response(
            serializer.errors,
            content_type="application/vnd.api+json",
            status=status.HTTP_400_BAD_REQUEST,
        )
