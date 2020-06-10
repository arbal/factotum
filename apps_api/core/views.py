import json
import datetime

from django.http import HttpResponse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken


class ObtainExpiringAuthToken(ObtainAuthToken):
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
            return HttpResponse(
                json.dumps(response_data), content_type="application/json"
            )

        return HttpResponse(
            json.dumps(serializer.errors),
            content_type="application/json",
            status=status.HTTP_400_BAD_REQUEST,
        )
