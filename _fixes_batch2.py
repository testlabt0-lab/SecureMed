import sys

# === 1.2 session_security.py: register_session stores jti, force_logout sets denylist ===
p = 'backend/apps/security/session_security.py'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()

# 1a. Add cache import at top
old_imports = (
    "import logging \n"
    "from django .core .cache import cache \n"
    "from django .utils import timezone \n"
    "from rest_framework_simplejwt .tokens import RefreshToken \n"
)
new_imports = (
    "import logging \n"
    "from django .core .cache import cache \n"
    "from django .utils import timezone \n"
    "from rest_framework_simplejwt .tokens import RefreshToken \n"
)
# imports already has cache, no change needed here
assert old_imports in c, 'session_security imports not found'

# 1b. Modify session_id extraction to use JWT jti
old_sid = "        session_id =request .session .session_key if hasattr (request ,'session')and request .session .session_key else ''\n"
new_sid = (
    "        session_id =''\n"
    "        if token is not None and isinstance (token ,dict ):\n"
    "            session_id =str (token .get ('jti',''))\n"
    "        if not session_id and hasattr (request ,'session')and request .session .session_key :\n"
    "            session_id =request .session .session_key \n"
)
assert old_sid in c, 'session_id line not found'
c = c.replace(old_sid, new_sid)

# 1c. Clear denylist when registering a new session (login clears prior force-logout)
old_clear = "        sessions .append (new_session )\n        cache .set (cache_key ,sessions ,timeout =86400 )# Comment_367\n"
new_clear = (
    "        sessions .append (new_session )\n"
    "        cache .set (cache_key ,sessions ,timeout =86400 )# Comment_367\n"
    "        # A successful login invalidates any prior force-logout denylist\n"
    "        cache .delete (f'token_denylist:{user .id }')\n"
)
assert old_clear in c, 'session append/set not found'
c = c.replace(old_clear, new_clear)

# 1d. force_logout_user: add denylist cache entry
old_flogout = (
    "        cache_key =f'active_sessions:{user_id }'\n"
    "        cache .delete (cache_key )\n"
    "\n"
    "        # Comment_369\n"
    "        # Comment_370\n"
    "        # Comment_371\n"
    "        logger .warning (f\"Force logout executed for user {user_id }\")\n"
)
new_flogout = (
    "        cache_key =f'active_sessions:{user_id }'\n"
    "        cache .delete (cache_key )\n"
    "\n"
    "        # Add user to token denylist so existing JWTs are rejected by\n"
    "        # BoundJWTAuthentication until the denylist entry expires or a new\n"
    "        # login clears it (see register_session).\n"
    "        cache .set (f'token_denylist:{user_id }',True ,timeout =86400 )\n"
    "\n"
    "        # Comment_369\n"
    "        # Comment_370\n"
    "        # Comment_371\n"
    "        logger .warning (f\"Force logout executed for user {user_id }\")\n"
)
assert old_flogout in c, 'force_logout body not found'
c = c.replace(old_flogout, new_flogout)

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)
print('session_security.py: OK')

# === 1.2 authentication.py: Add denylist check ===
p = 'backend/apps/security/authentication.py'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()

# Add cache import
old_auth_imports = (
    "import hashlib \n"
    "from rest_framework_simplejwt .authentication import JWTAuthentication \n"
    "from rest_framework_simplejwt .exceptions import AuthenticationFailed \n"
)
new_auth_imports = (
    "import hashlib \n"
    "from django .core .cache import cache \n"
    "from rest_framework_simplejwt .authentication import JWTAuthentication \n"
    "from rest_framework_simplejwt .exceptions import AuthenticationFailed \n"
)
assert old_auth_imports in c, 'auth imports not found'
c = c.replace(old_auth_imports, new_auth_imports)

# Add denylist check after user extraction
old_user = (
    "        user ,validated_token =auth_result \n"
    "\n"
    "        # Comment_309\n"
)
new_user = (
    "        user ,validated_token =auth_result \n"
    "\n"
    "        # Check token denylist — rejects JWTs issued before a force-logout\n"
    "        if cache .get (f'token_denylist:{user .id }'):\n"
    "            raise AuthenticationFailed ('الجلسة غير صالحة. يرجى تسجيل الدخول مرة أخرى.',code ='session_invalidated')\n"
    "\n"
    "        # Comment_309\n"
)
assert old_user in c, 'auth user extraction not found'
c = c.replace(old_user, new_user)

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)
print('authentication.py: OK')

# === 1.2 accounts/views.py: get_tokens_for_user returns jti + reorder register_session ===
p = 'backend/apps/accounts/views.py'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()

# Add jti to get_tokens_for_user return
old_ret = (
    "    return {\n"
    "    'refresh':str (refresh ),\n"
    "    'access':str (refresh .access_token ),\n"
    "    }\n"
)
new_ret = (
    "    return {\n"
    "    'refresh':str (refresh ),\n"
    "    'access':str (refresh .access_token ),\n"
    "    'jti':str (refresh ['jti']),\n"
    "    }\n"
)
assert old_ret in c, 'get_tokens_for_user return not found'
c = c.replace(old_ret, new_ret)

# Reorder LoginView: tokens first, then register_session with token
old_login = (
    "        SessionManager .register_session (user ,request )\n"
    "\n"
    "        tokens =get_tokens_for_user (user ,request )\n"
    "        log_security_event (\n"
)
new_login = (
    "        tokens =get_tokens_for_user (user ,request )\n"
    "\n"
    "        SessionManager .register_session (user ,request ,token =tokens )\n"
    "        log_security_event (\n"
)
assert old_login in c, 'login register_session call not found'
c = c.replace(old_login, new_login)

# Reorder BiometricLoginView: tokens first, then register_session with token
old_bio = (
    "        SessionManager .register_session (user ,request )\n"
    "\n"
    "        tokens =get_tokens_for_user (user ,request )\n"
    "        log_security_event (\n"
    "        user =user ,\n"
    "        event_type ='BIOMETRIC_LOGIN_SUCCESS',\n"
)
new_bio = (
    "        tokens =get_tokens_for_user (user ,request )\n"
    "\n"
    "        SessionManager .register_session (user ,request ,token =tokens )\n"
    "        log_security_event (\n"
    "        user =user ,\n"
    "        event_type ='BIOMETRIC_LOGIN_SUCCESS',\n"
)
assert old_bio in c, 'biometric register_session call not found'
c = c.replace(old_bio, new_bio)

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)
print('accounts/views.py: OK')
