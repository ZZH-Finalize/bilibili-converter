from pydantic import BaseModel

class Vidinfo(BaseModel):
    type: int
    title: str
    owner: str
    output_path: str
