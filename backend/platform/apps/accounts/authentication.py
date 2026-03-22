from __future__ import annotations

from datetime import timedelta

from django.utils import timezone
from rest_framework import exceptions
from rest_framework.authentication import TokenAuthentication, get_authorization_header
from rest_framework.authtoken.models import Token


TOKEN_VALIDITY_DAYS = 7


class ExpiringTokenAuthentication(TokenAuthentication):
    keyword = "Token"

    def authenticate_credentials(self, key):
        user_auth_tuple = super().authenticate_credentials(key)
        user, token = user_auth_tuple
        self._ensure_token_valid(token)
        return user, token

    def _ensure_token_valid(self, token: Token) -> None:
        expires_at = token.created + timedelta(days=TOKEN_VALIDITY_DAYS)
        if expires_at <= timezone.now():
            token.delete()
            raise exceptions.AuthenticationFailed("登录已过期，请重新登录。")


class QueryStringExpiringTokenAuthentication(ExpiringTokenAuthentication):
    def authenticate(self, request):
        header = get_authorization_header(request)
        if header:
            return super().authenticate(request)

        key = request.query_params.get("access_token", "").strip()
        if not key:
            return None

        return self.authenticate_credentials(key)
