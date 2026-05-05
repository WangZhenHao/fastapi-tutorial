from fastapi import FastAPI

test = FastAPI()


@test.get('/')
def root():
    return {"message": "Hello World"}