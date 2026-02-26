from fastapi import FastAPI

from graph_src_v2.custom_routes.tools import router as capabilities_router

app = FastAPI(title="graph_src_v2 custom routes")
app.include_router(capabilities_router)
