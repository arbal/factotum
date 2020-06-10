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

        utc_now = datetime.datetime.utcnow()

        if token.created < utc_now - datetime.timedelta(
            milliseconds=env.FACTOTUM_WS_TOKEN_TTL
        ):
            raise exceptions.AuthenticationFailed("Token has expired")

        return token.user, token
