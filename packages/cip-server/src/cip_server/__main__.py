import argparse

from cip_server.api import app
import uvicorn


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument("--host", type=str, default="127.0.0.1", help="the host address for the api to listen on. defaults to 127.0.0.1")
    parser.add_argument("--port", type=int, default=8000, help="the port for the api to bind to. Defaults to 8000")
    parser.add_argument("--workers", type=int, help="the number of uvicorn workers to spawn")
    parser.add_argument("--log-level", type=str, help="the logging level for the api and uvicorn's log outputs")

    args = parser.parse_args()

    uvicorn.run(app=app, host=args.host, port=args.port, workers=args.workers, log_level=args.log_level)

if __name__ == "__main__":
    main()