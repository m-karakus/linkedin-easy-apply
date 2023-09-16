from fastapi import FastAPI, Request
from linkedin_apply import main as easyapply
import threading
import sys


easyapply()
# app = FastAPI()

# @app.get('/health')
# async def main_route(request: Request):
#     threading_count = threading.active_count()
#     print(threading_count)
    
#     if threading_count <=1:
#         t1 = threading.Thread(target=easyapply,args=())
#         t1.start()
#     else:
#         pass
#     return {"Called from": request.url.path}

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app,host="0.0.0.0", port=8899)