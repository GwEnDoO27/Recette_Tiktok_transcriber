import uvicorn #type: ignore

if __name__ == '__main__':
    uvicorn.run(
        "Backend.main:app",
        host='localhost',
        port=8001,
        reload=True,
        log_level='info'
    )