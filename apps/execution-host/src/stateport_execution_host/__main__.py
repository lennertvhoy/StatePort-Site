"""Boot the execution-host daemon from its typed environment contract.

Environment (rendered by the stable-host Quadlet and operator provisioning):
- ``STATEPORT_HOST_SOCKET`` / ``STATEPORT_EXECUTION_HOST_SOCKET``: confined
  control socket path (host ``/run/stateport/execution-control/control.sock``,
  container ``/run/stateport-execution/control.sock``).
- ``STATEPORT_EXECUTION_HOST_STATE_DIR``: durable ledger root.
- ``STATEPORT_ENGINE_SOCKET``: the execution user's own rootless Podman
  socket.  Control-plane sockets are refused by the engine adapter.
- ``STATEPORT_PODMAN_BINARY``: ``podman`` on a host, ``podman-remote`` in the
  image.
- ``STATEPORT_EXECUTION_HOST_SOCKET_GROUP[_GID]`` and
  ``STATEPORT_EXECUTION_HOST_ALLOWED_CLIENT_USER[_UID]``: confinement checks.
"""

from __future__ import annotations

import os
import signal
import sys

from execution_host.daemon import DaemonBootError, DaemonConfig, ExecutionHostDaemon
from execution_host.engine import EngineError, PodmanCliEngine


def main() -> int:
    config = DaemonConfig.from_env()
    try:
        engine = PodmanCliEngine(
            binary=os.environ.get("STATEPORT_PODMAN_BINARY", "podman"),
            socket_path=os.environ.get("STATEPORT_ENGINE_SOCKET") or None,
        )
    except EngineError as exc:
        print(f"stateport-execution-host boot refused: {exc}", file=sys.stderr)
        return 2
    daemon = ExecutionHostDaemon(config, engine)
    try:
        daemon.boot()
    except DaemonBootError as exc:
        print(f"stateport-execution-host boot refused: {exc}", file=sys.stderr)
        return 2

    def _terminate(signum: int, frame: object) -> None:
        daemon.shutdown()
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, _terminate)
    signal.signal(signal.SIGINT, _terminate)
    print(
        f"stateport-execution-host contract v1 listening on {config.socket_path}",
        file=sys.stderr,
        flush=True,
    )
    try:
        daemon.serve_forever()
    finally:
        daemon.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
