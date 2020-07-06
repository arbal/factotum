import datetime

from rest_framework.authentication import TokenAuthentication
from rest_framework import exceptions

from factotum.environment import env


class ExpiringTokenAuthentication(TokenAuthentication):
    keyword = "Bearer"

    def authenticate_credentials(self, key):
        model = self.get_model()

        try:
            token = model.objects.get(key=key)
        except model.DoesNotExist:
            raise exceptions.AuthenticationFailed("Invalid token")

        if not token.user.is_active:
            raise exceptions.AuthenticationFailed("User inactive or deleted")

        now = datetime.datetime.now()

        if token.created < now - datetime.timedelta(
            milliseconds=env.FACTOTUM_WS_TOKEN_TTL
        ):
            raise exceptions.AuthenticationFailed("Token has expired")

        return token.user, token
