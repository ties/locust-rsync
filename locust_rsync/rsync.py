"""
rsync wrapper, and locust rsync user.

Enables load testing of rsync servers using locust.
"""
import time
import logging
import tempfile
from pathlib import Path
from typing import List, Optional

import gevent
from gevent.subprocess import Popen, PIPE

from locust import User


LOG = logging.getLogger(__name__)


class RsyncClient:
    """An rsync wrapper."""

    host: str
    temp_dir: Path
    # arguments from routinator rsync.rs:570
    rsync_flags: List[str] = ["-rltz", "--delete"]
    rsync_binary: str = "rsync"
    timeout: int = 300
    """
    A wrapper for an rsync subprocess.

    It proxies any function fall to the `/module/<path>` on the rsync server
    with the standard flags.
    """

    def __init__(
        self,
        temp_dir: str,
        host,
        request_event,
        rsync_flags: Optional[List[str]] = None,
        rsync_binary: Optional[str] = None,
    ):
        """
        Create an rsync client for given target.

        Filename (and module) are only passed when calling
        `client.call_rsync([path])`.
        """
        self._request_event = request_event
        self.temp_dir = Path(temp_dir).resolve()
        self.host = host
        if rsync_flags:
            self.rsync_flags = rsync_flags
        if rsync_binary:
            self.rsync_binary = rsync_binary

    def __call_rsync(self, name: str, *args, **kwargs):
        """Call the rsync binary."""
        # Get rsync://{self.host}/{name}
        url = f"rsync://{self.host}/{name}"

        # Create full path
        target_path = (self.temp_dir / name).resolve()
        target_path.parent.mkdir(parents=True, exist_ok=True)

        LOG.info("rsyncing %s to %s", url, target_path)

        # Validate there is no directory traversal
        assert self.temp_dir in target_path.parents

        args = [self.rsync_binary]
        args.extend(self.rsync_flags)
        args.extend([url, str(target_path)])

        LOG.info("Running %s", " ".join(args))

        res = Popen(args, stdout=PIPE, stderr=PIPE)
        if not gevent.wait([res], self.timeout):
            res.kill()

        if res.returncode != 0:
            raise ValueError(
                "Process exited with %d, stderr: %s", res.returncode, res.stderr.read()
            )

        out = res.stdout.read() + res.stderr.read()
        return out

    def get(self, name):
        """Rsync 'get request'."""
        start_time = time.perf_counter()
        # TODO: calculate byte transfered and files transfered from rsync
        request_meta = {
            "request_type": "rsync",
            "name": name,
            "response_length": 0,
            "response": None,
            "context": {},
            "exception": None,
        }
        try:
            request_meta["response"] = self.__call_rsync(name)
        except Exception as e:
            request_meta["exception"] = e
        request_meta["response_time"] = (time.perf_counter() - start_time) * 1000
        self._request_event.fire(**request_meta)


class RsyncUser(User):
    """A minimal Locust user class that provides an XmlRpcClient to its subclasses."""

    temp_dir: tempfile.TemporaryDirectory

    abstract = True  # dont instantiate this as an actual user when running Locust

    def __init__(self, environment):
        """
        Initialise RsyncUser.

        The major settings (`self.host`) are passed as instance variables.
        """
        super().__init__(environment)
        assert (
            "rsync://" not in self.host
        ), "host should just contain the hostname, not rsync://"
        assert not self.host.endswith(
            "/"
        ), "host should contain the hostname and not end with /"
        self.client = RsyncClient(
            self.temp_dir.name, self.host, request_event=environment.events.request
        )
