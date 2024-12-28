from fastapi.responses import JSONResponse
from typing import Optional, Any


def create_response(status: str, message: str, data: Optional[Any] = None) -> JSONResponse:
    content = {"status": status, "message": message}
    if data is not None:
        content["data"] = data

    return JSONResponse(content=content)
