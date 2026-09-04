from pydantic import BaseModel


class ToolSchema(BaseModel):
    name: str
    description: str
    input_schema: dict
    output_schema: dict
