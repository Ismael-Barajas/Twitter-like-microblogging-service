import hug
import requests
import time
import threading
import copy

registry = {
    "users": {},
    "timelines": {},
    "likes": {},
    "polls": {}
}


# Runs health checks on services
def health_check():
    _lock = threading.Lock()
    while 1:
        for api in registry:
            for url in copy.deepcopy(registry[api]):
                try:
                    r = requests.get(f"{url}/health-check")
                    r.raise_for_status()
                except requests.HTTPError:
                    with _lock:
                        del registry[api][url]
        time.sleep(20)


# Starts daemon thread that runs forever, that checks health of all services
@hug.startup()
def run_heath_check(api):
    threading.Thread(target=health_check, daemon=True).start()


# Arguments to inject into route functions
@hug.directive()
def set_registry(**kwargs):
    return registry


# Services registering to registry
@hug.post("/register")
def register(
    response,
    service: hug.types.text,
    url: hug.types.text,
    db: set_registry
):
    if service in db:
        db[service][url] = True
        return db
    response.status = hug.falcon.HTTP_422
    return {"status": hug.falcon.HTTP_422, "message": f"{service} does not exist."}


@hug.get("/available/{service}")
def available_services(response, service, db: set_registry):
    if service in db:
        return {f"{service}": db[service]}
    response.status = hug.falcon.HTTP_404
    return {"status": hug.falcon.HTTP_404, "message": f"{service} does not exist."}
