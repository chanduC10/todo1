from fastapi import FastAPI, HTTPException
from models import Todo
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import redis
import json

# Initialize FastAPI app
app = FastAPI()

# MongoDB setup
client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client.todo_db
todo_collection = db.todos

# Redis setup (default host and port)
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Health check route
@app.get("/")
async def root():
    return {"message": "Todo App is Running ✅"}

# GET all todos (with Redis cache)
@app.get("/todos")
async def get_todos():
    # 1. Check Redis cache first
    cached_todos = redis_client.get("todos_cache")
    if cached_todos:
        print("📦 Returning from Redis cache")
        return json.loads(cached_todos)

    # 2. If not in cache, get from MongoDB
    todos = []
    cursor = todo_collection.find({})
    async for todo in cursor:
        todo["_id"] = str(todo["_id"])  # Convert ObjectId to string
        todos.append(todo)

    # 3. Store result in Redis
    redis_client.set("todos_cache", json.dumps(todos))  # Optional: add ex=60 for expiration
    print("✅ Fetched from DB and stored in Redis")
    return todos

# POST a new todo
@app.post("/todos")
async def create_todo(todo: Todo):
    todo_dict = todo.dict()
    result = await todo_collection.insert_one(todo_dict)
    todo_dict["_id"] = str(result.inserted_id)

    # Invalidate Redis cache
    redis_client.delete("todos_cache")

    return {"message": "Todo added", "todo": todo_dict}

# PUT (update) a todo by ID
@app.put("/todos/{todo_id}")
async def update_todo(todo_id: str, updated_todo: Todo):
    result = await todo_collection.update_one(
        {"_id": ObjectId(todo_id)},
        {"$set": updated_todo.dict()}
    )
    if result.modified_count == 1:
        redis_client.delete("todos_cache")  # Invalidate cache
        return {"message": "Todo updated"}
    raise HTTPException(status_code=404, detail="Todo not found")

# DELETE a todo by ID
@app.delete("/todos/{todo_id}")
async def delete_todo(todo_id: str):
    result = await todo_collection.delete_one({"_id": ObjectId(todo_id)})
    if result.deleted_count == 1:
        redis_client.delete("todos_cache")  # Invalidate cache
        return {"message": "Todo deleted"}
    raise HTTPException(status_code=404, detail="Todo not found")
