from fastapi import FastAPI, Request,Response,status,APIRouter
from fastapi.responses import RedirectResponse,HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from routes import rating_instance_routes, rating_model_factors_routes, rating_model_factors_routes
from security import AuthHandler, RequiresLoginException
from routes import customer_routes, statement_routes,businessunits_routes,rating_scale_routes,templates_routes, fs_line_item_routes,rating_model_config_routes
from fastapi.encoders import jsonable_encoder
from fastapi import FastAPI, Depends, HTTPException, Request, Form
from fastapi.responses import RedirectResponse,HTMLResponse,FileResponse
from db.database import SessionLocal 
from models.models import User
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
from passlib.context import CryptContext
from starlette.middleware.base import BaseHTTPMiddleware
from debug_toolbar.middleware import DebugToolbarMiddleware
from jose import jwt

from fastapi import FastAPI, Request, Response
from dependencies import get_db

import smtplib
from datetime import datetime,date
from email.message import EmailMessage

import logging
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='login_alerts.log'
)
logger = logging.getLogger(__name__)
last_login_date: Optional[date] = None
app = FastAPI(debug=True)
# app.add_middleware(DebugToolbarMiddleware, panels=["debug_toolbar.panels.sqlalchemy.SQLAlchemyPanel"] )
# app.add_middleware(DebugToolbarMiddleware  )
# Mount static files
app.mount("/static", StaticFiles(directory="../static"), name="static")

# Set up Jinja2 templates
templates = Jinja2Templates(directory="../frontend/templates")

auth_handler = AuthHandler()
# redirection block
# Middleware to add user to request state
# class UserMiddleware(BaseHTTPMiddleware):
#     async def dispatch(self, request: Request, call_next):
#         # Initialize request.state.user as None
#         request.state.user = None
        
#         # Skip auth for public paths
#         if request.url.path in ["/", "/login", "/static"]:
#             response = await call_next(request)
#             return response

#         try:
#             # Get token from cookie
#             token = request.cookies.get("Authorization")
#             if token:
#                 # Decode token and set user in request state
#                 email = auth_handler.decode_token(token)
#                 request.state.user = email
#         except Exception as e:
#             # If there's an error, user remains None
#             pass

#         # Modify templates to always include user from request state
#         templates.env.globals["user"] = request.state.user
        
#         response = await call_next(request)
#         return response

# Add middleware to app
# app.add_middleware(UserMiddleware)

# Update Jinja2Templates to include user by default
# @app.middleware("http")
# async def add_template_context(request: Request, call_next):
#     response = await call_next(request)
#     if hasattr(response, "context"):
#         response.context["user"] = request.state.user
#     return response

# app.include_router(customer_routes.router,dependencies=[Depends(auth_handler.auth_wrapper)])
app.include_router(customer_routes.router)
app.include_router(statement_routes.router)
app.include_router(rating_instance_routes.router)
app.include_router(businessunits_routes.router)
app.include_router(rating_scale_routes.router)
app.include_router(templates_routes.router)
app.include_router(fs_line_item_routes.router)
app.include_router(rating_model_config_routes.router)
app.include_router(rating_model_factors_routes.router)
# redirection block
@app.exception_handler(RequiresLoginException)
async def exception_handler(request: Request, exc: RequiresLoginException) -> Response:
    ''' this handler allows me to route the login exception to the login page.'''
    return RedirectResponse(url='/')        



@app.middleware("http")
async def create_auth_header(
    request: Request,
    call_next,):
    '''
    Check if there are cookies set for authorization. If so, construct the
    Authorization header and modify the request (unless the header already
    exists!)
    '''
    if ("Authorization" not in request.headers 
        and "Authorization" in request.cookies
        ):
        access_token = request.cookies["Authorization"]
        
        request.headers.__dict__["_list"].append(
            (
                "authorization".encode(),
                 f"Bearer {access_token}".encode(),
            )
        )
    elif ("Authorization" not in request.headers 
        and "Authorization" not in request.cookies
        ): 
        request.headers.__dict__["_list"].append(
            (
                "authorization".encode(),
                 f"Bearer 12345".encode(),
            )
        )
        
    
    response = await call_next(request)
    return response    

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("login/index.html",
     {"request": request,"admin":False})

# @app.middleware("http")
# async def create_auth_header(request: Request, call_next):
#     try:
#         # Only modify headers if we have a cookie but no Authorization header
#         if "Authorization" not in request.headers and "Authorization" in request.cookies:
#             access_token = request.cookies["Authorization"]
#             # Create a new list of headers
#             headers = [(k.lower().encode(), v.encode()) for k, v in request.headers.items()]
#             headers.append(
#                 ("authorization".encode(), f"Bearer {access_token}".encode())
#             )
#             # Update request headers
#             request.scope.update(headers=headers)
        
#         # Call the next middleware/route handler
#         response = await call_next(request)
#         return response
    
#     except Exception as e:
#         # If any error occurs, return a valid response
#         return RedirectResponse(url='/', status_code=302)
# Include routers
def create_protected_router(prefix: str):
    router = APIRouter(
        prefix=f"/{prefix}",
        tags=[prefix],
        dependencies=[Depends(auth_handler.auth_wrapper)]
    )
    return router

# # Protected routers
# customer_router = create_protected_router("customers")
# statement_router = create_protected_router("statements")
# rating_model_router = create_protected_router("rating")

# app.include_router(customer_router)
# app.include_router(statement_router)
# app.include_router(rating_model_router)



        

    
    # response = await call_next(request)
    # return response   
@app.get("/register/", response_class=HTMLResponse)
async def registration(request: Request):
    return templates.TemplateResponse("login/register.html",
     {"request": request})


@app.post("/register/", response_class=HTMLResponse)
async def register(request: Request, email: str = Form(...), password: str = Form(...),db:Session = Depends(get_db)):
    password_hash= auth_handler.get_hash_password(password)
    user = User(email = email,
        password= password_hash)    
    # query = users.insert().values(email = user.email,
    #     password= auth_handler.get_hash_password(user.password))
    # result = await database.execute(query)
    # doc=Document(name=docName,page_count=page_count, url = path)
    db.add(user)
    db.commit()
    db.refresh(user)
    # TODO verify success and handle errors
    response = templates.TemplateResponse("login/success.html", 
              {"request": request, "success_msg": "Registration Successful!",
              "path_route": '/', "path_msg": "Click here to login!"})
    return response

@app.post("/login/")
async def sign_in(request: Request, response: Response,
    email: str = Form(...), password: str = Form(...)):
    try:
        user = User(email = email,
            password= password)  
        if await auth_handler.authenticate_user(user.email, user.password):
            atoken = auth_handler.create_access_token(user.email)
            # response = templates.TemplateResponse("login/success.html", 
            #   {"request": request, "USERNAME": user.email, "success_msg": "Welcome back! ",
            #   "path_route": '/uploadDocs', "path_msg": "Go to PatraChitra!"})
            response = RedirectResponse(
                url='/customers',  # Redirect to customers page
                status_code=status.HTTP_303_SEE_OTHER  # Using 303 for POST-to-GET redirect
            )
            response.set_cookie(key="Authorization", value= f"{atoken}", httponly=True, samesite='lax',)
            return response
        else:
            return templates.TemplateResponse("error.html",
            {"request": request, 'detail': 'Incorrect Username or Password', 'status_code': 404 })
    
    except Exception as err:
        return templates.TemplateResponse("login/error.html",
            {"request": request, 'detail': 'Incorrect Username or Password', 'status_code': 401 })
# @app.get("/")
# async def root(request: Request):
#     return templates.TemplateResponse("index.html", {"request": request})
# Email configuration
EMAIL_CONFIG = {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "sender_email": "ashley.cherian@gmail.com",
    "sender_password": "jnjt dpwl atxu vmkk",  # Use app-specific password for Gmail
    "recipient_email": "ashley.cherian@gmail.com"
}
import pytz
@app.get("/send-alert")
def send_alert_email(login_time: datetime=  datetime.now(pytz.UTC)):
    """Send an email alert for the first login of the day."""
    try:
        msg = EmailMessage()
        msg.set_content(f"First login of the day detected at {login_time}")
        
        msg['Subject'] = 'First Login Alert'
        msg['From'] = EMAIL_CONFIG["sender_email"]
        msg['To'] = EMAIL_CONFIG["recipient_email"]
        
        with smtplib.SMTP(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["smtp_port"]) as server:
            server.starttls()
            server.login(EMAIL_CONFIG["sender_email"], EMAIL_CONFIG["sender_password"])
            server.send_message(msg)
            
        logger.info("Alert email sent successfully")
    except Exception as e:
        logger.error(f"Failed to send alert email: {str(e)}")
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)