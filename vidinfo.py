from pydantic import BaseModel

class vidinfo(BaseModel):
    type: int
    title: str
    owner: str
    output_path: str
