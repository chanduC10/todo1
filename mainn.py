from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import redis
import json

# ───────────────────────────────────────────────────
# 🧱 MongoDB + Redis Setup
# ───────────────────────────────────────────────────

# MongoDB setup
client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client.todo_db
todo_collection = db.todos

# Redis setup
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# ───────────────────────────────────────────────────
# ✅ FastAPI app
# ───────────────────────────────────────────────────

app = FastAPI()

# ───────────────────────────────────────────────────
# 📘 Pydantic model for Todo
# ───────────────────────────────────────────────────

class Todo(BaseModel):
    id: int = Field(..., gt=0)
    item: str = Field(..., min_length=2, max_length=100)

# ───────────────────────────────────────────────────
# 🔁 Redis Helpers
# ───────────────────────────────────────────────────

def get_cached_todos():
    cached_data = redis_client.get("todos_cache")
    if cached_data:
        print("📦 Returned from Redis cache")
        return json.loads(cached_data)
    return None

def set_cached_todos(data):
    redis_client.set("todos_cache", json.dumps(data), ex=60)
    print("🧠 Stored in Redis")

def clear_cache():
    redis_client.delete("todos_cache")
    print("🧹 Redis cache cleared")

# ───────────────────────────────────────────────────
# 📚 MongoDB Helpers
# ───────────────────────────────────────────────────

async def get_todos_from_db():
    todos = []
    cursor = todo_collection.find({})
    async for todo in cursor:
        todo["_id"] = str(todo["_id"])  # ObjectId to string
        todos.append(todo)
    return todos

async def add_todo_to_db(todo: Todo):
    todo_dict = todo.dict()
    result = await todo_collection.insert_one(todo_dict)
    todo_dict["_id"] = str(result.inserted_id)
    return todo_dict

async def update_todo_in_db(todo_id: str, todo: Todo):
    result = await todo_collection.update_one(
        {"_id": ObjectId(todo_id)},
        {"$set": todo.dict()}
    )
    return result.modified_count

async def delete_todo_from_db(todo_id: str):
    result = await todo_collection.delete_one({"_id": ObjectId(todo_id)})
    return result.deleted_count

# ───────────────────────────────────────────────────
# 🚪 API Routes
# ───────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"message": "Todo App is Running ✅"}

# ✅ GET all todos (uses Redis cache)
@app.get("/todos")
async def get_todos():
    cached = get_cached_todos()
    if cached:
        return cached

    todos = await get_todos_from_db()
    set_cached_todos(todos)
    return todos

# ✅ POST a new todo
@app.post("/todos")
async def create_todo(todo: Todo):
    new_todo = await add_todo_to_db(todo)
    clear_cache()
    return {"message": "Todo added", "todo": new_todo}

# ✅ PUT update a todo
@app.put("/todos/{todo_id}")
async def update_todo(todo_id: str, updated_todo: Todo):
    updated = await update_todo_in_db(todo_id, updated_todo)
    if updated:
        clear_cache()
        return {"message": "Todo updated"}
    raise HTTPException(status_code=404, detail="Todo not found")

# ✅ DELETE a todo
@app.delete("/todos/{todo_id}")
async def delete_todo(todo_id: str):
    deleted = await delete_todo_from_db(todo_id)
    if deleted:
        clear_cache()
        return {"message": "Todo deleted"}
    raise HTTPException(status_code=404, detail="Todo not found")
