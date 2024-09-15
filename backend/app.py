from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from routes import customer_routes, statement_routes,rating_model_routes
app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="../static"), name="static")

# Set up Jinja2 templates
templates = Jinja2Templates(directory="../frontend/templates")

# Import route modules

# Include routers
app.include_router(customer_routes.router)
app.include_router(statement_routes.router)
app.include_router(rating_model_routes.router)

@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)