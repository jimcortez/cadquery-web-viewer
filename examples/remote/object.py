# Optional: enable logging to see what's happening
import logging
import os
import sys

from build123d import *  # Also works with cadquery objects!
from build123d import Compound

logging.basicConfig(level=logging.DEBUG)

from cadquery_web_viewer import show

REMOTE_HOST = "localhost"
REMOTE_PORT = 32323
# Image tag used in the printed `docker run` hint (override when testing another tag).
DOCKER_IMAGE = os.environ.get("CADQUERY_WEB_VIEWER_DOCKER_IMAGE", "cadquery-web-viewer:test")
# Published container port (Flask default inside the image).
CONTAINER_PORT = 32323


def _docker_server_command() -> str:
    return (
        "docker run --rm --platform linux/amd64 "
        f"-p {REMOTE_PORT}:{CONTAINER_PORT} "
        "-e CADQUERY_WEB_VIEWER_HOST=0.0.0.0 "
        f"{DOCKER_IMAGE}"
    )


def _cli_server_command() -> str:
    return f"cadquery-web-viewer --host {REMOTE_HOST} --port {REMOTE_PORT}"


def _wait_for_user_to_start_server() -> None:
    if "CI" in os.environ:
        print("Skipping interactive remote demo under CI.", file=sys.stderr)
        sys.exit(0)
    docker_cmd = _docker_server_command()
    cli_cmd = _cli_server_command()
    print()
    print("In another terminal, start the viewer and API using either option below, then come back here.")
    print()
    print("Docker (from the repo root, after `docker build --platform linux/amd64 -t "
        f"{DOCKER_IMAGE} .`):")
    print(f"  {docker_cmd}")
    print()
    print("Command line (with cadquery-web-viewer on your PATH, e.g. after `uv sync` or `pip install`):")
    print(f"  {cli_cmd}")
    print()
    input("Press Enter when the server is running... ")
    print()


# %%

_wait_for_user_to_start_server()

# Same model as examples/in-process/object.py
with BuildPart() as example:
    Box(10, 10, 5)
    Cylinder(4, 5, mode=Mode.SUBTRACT)

example.color = (0.1, 0.3, 0.1, 1)  # RGBA
to_highlight = example.edges().group_by(Axis.Z)[-1]
example_hl = Compound(to_highlight).translate((0, 0, 1e-3))
example_hl.color = (1, 1, 0.0, 1)

texture = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABIAAAASAQAAAAB+tbP6AAAAQ0lEQVQI12P4b3+A4Z/8AYYHBw8w"
    "HHxwgOH8HyD+AsRPDjDMP+fAYD+fgcESiGfYOTCcqTnAcK4GogakFqQHpBdoBgAbGiPSbdzkhgAAAABJRU5ErkJggg=="
)

show(
    example,
    example_hl,
    texture=texture,
    server_type="remote",
    remote_options={"host": REMOTE_HOST, "port": REMOTE_PORT},
)
