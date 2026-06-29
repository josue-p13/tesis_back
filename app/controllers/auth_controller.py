from fastapi import APIRouter, Request, HTTPException
from authlib.integrations.starlette_client import OAuth
from app.core.config import config
from starlette.responses import RedirectResponse

router = APIRouter(prefix="/auth", tags=["Autenticación OAuth"])

oauth = OAuth()

oauth.register(
    name='google',
    client_id=config.GOOGLE_CLIENT_ID,
    client_secret=config.GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

oauth.register(
    name='microsoft',
    client_id=config.MS_CLIENT_ID,
    client_secret=config.MS_CLIENT_SECRET,
    server_metadata_url=f'https://login.microsoftonline.com/{config.MS_TENANT_ID}/v2.0/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile User.Read'}
)

@router.get("/login/google")
async def login_google(request: Request):
    """Redirige al usuario a la página de login de Google."""
    return await oauth.google.authorize_redirect(request, config.OAUTH_REDIRECT_URI, state="login")

@router.get("/register/google")
async def register_google(request: Request):
    """Redirige al usuario a la página de registro de Google."""
    return await oauth.google.authorize_redirect(request, config.OAUTH_REDIRECT_URI, state="register")

@router.get("/login/microsoft")
async def login_microsoft(request: Request):
    """Redirige al usuario a la página de login de Microsoft."""
    return await oauth.microsoft.authorize_redirect(request, config.MS_OAUTH_REDIRECT_URI, state="login")

@router.get("/register/microsoft")
async def register_microsoft(request: Request):
    """Redirige al usuario a la página de registro de Microsoft."""
    return await oauth.microsoft.authorize_redirect(request, config.MS_OAUTH_REDIRECT_URI, state="register")

@router.get("/callback")
async def auth_callback(request: Request):
    """Recibe la respuesta de Google y la manda al Frontend para procesar."""
    return await _procesar_callback(request, oauth.google)

@router.get("/microsoft/callback")
async def microsoft_callback(request: Request):
    """Recibe la respuesta de Microsoft."""
    return await _procesar_callback(request, oauth.microsoft)

async def _procesar_callback(request: Request, client):
    """Lógica unificada para procesar el callback de cualquier proveedor OAuth."""
    try:
        state = request.query_params.get("state", "login")
        token = await client.authorize_access_token(request)
        user_info = token.get('userinfo')
        
        if not user_info:
            user_info = token
            
        email = user_info.get('email') or user_info.get('preferred_username')
        name = user_info.get('name', email.split('@')[0] if email else "Usuario")
        
        if not email:
            raise HTTPException(status_code=400, detail="No se pudo obtener el email del proveedor")

        return RedirectResponse(
            url=f"{config.FRONTEND_URL}/api/auth/callback?email={email}&name={name}&mode={state}"
        )
    except Exception as e:
        return RedirectResponse(url=f"{config.FRONTEND_URL}/login?status=error")
