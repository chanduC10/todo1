# main.py
from fastapi import FastAPI, HTTPException
from models import Todo
from motor.motor_asyncio import AsyncIOMotorClient  #way to talk to MongoDB asynchronously
from bson import ObjectId  # ObjectId is used to handle MongoDB's unique identifiers

app = FastAPI()

client = AsyncIOMotorClient("mongodb://localhost:27017") # Connect to MongoDB at the specified URI
db = client.todo_db  # Database name
todo_collection = db.todos # Collection name


@app.get("/")
async def root():
    return {"message": "Todo App is Running ✅"}

@app.get("/todos")
async def get_todos():
    todos = []
    cursor = todo_collection.find({})  # Find all documents in the collection
    async for todo in cursor:
        todo["_id"] = str(todo["_id"])  # Convert ObjectId to string
        todos.append(todo)
    return todos


@app.post("/todos")
async def create_todo(todo: Todo):
    todo_dict = todo.dict()  # Convert Pydantic to regular Python dict
    result = await todo_collection.insert_one(todo_dict)  #saves it to mangoDB
    todo_dict["_id"] = str(result.inserted_id)  #mangdb having unique id, it converts it to string
    return {"message": "Todo added", "todo": todo_dict}

@app.put("/todos/{todo_id}")
async def update_todo(todo_id: str, updated_todo: Todo):
    result = await todo_collection.update_one(
        {"_id": ObjectId(todo_id)},
        {"$set": updated_todo.dict()}
    )
    if result.modified_count == 1:
        return {"message": "Todo updated"}
    raise HTTPException(status_code=404, detail="Todo not found")


@app.delete("/todos/{todo_id}")
async def delete_todo(todo_id: str):
    result = await todo_collection.delete_one({"_id": ObjectId(todo_id)})
    if result.deleted_count == 1:
        return {"message": "Todo deleted"}
    raise HTTPException(status_code=404, detail="Todo not found")

