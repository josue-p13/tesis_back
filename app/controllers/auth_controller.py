from fastapi import APIRouter, Request, HTTPException
from authlib.integrations.starlette_client import OAuth
from app.core.config import config
from starlette.responses import RedirectResponse

router = APIRouter(prefix="/auth", tags=["Autenticación Google"])

# Configuración de OAuth
oauth = OAuth()
oauth.register(
    name='google',
    client_id=config.GOOGLE_CLIENT_ID,
    client_secret=config.GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

@router.get("/login/google")
async def login_google(request: Request):
    """Redirige al usuario a la página de login de Google."""
    # OAUTH_REDIRECT_URI debe ser: http://localhost:8000/auth/callback
    return await oauth.google.authorize_redirect(request, config.OAUTH_REDIRECT_URI)

@router.get("/callback")
async def auth_callback(request: Request):
    """Recibe la respuesta de Google y la manda al Frontend para procesar."""
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo')
        if not user_info:
            raise HTTPException(status_code=400, detail="No se pudo obtener información")
        
        email = user_info['email']
        name = user_info.get('name', email.split('@')[0])
        
        # Redirigimos al Frontend pasando los datos necesarios
        # Usamos encodeURIComponent implícito al construir la URL
        return RedirectResponse(
            url=f"http://localhost:3000/api/auth/google-callback?email={email}&name={name}"
        )
        
    except Exception as e:
        # Podrías usar un logger aquí
        return RedirectResponse(url="http://localhost:3000/login?status=error")
