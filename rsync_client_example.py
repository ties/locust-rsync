"""Example of rsync user usage."""
import logging
import tempfile

from locust_plugins import run_single_user
from locust import task

from locust_rsync import RsyncUser


# The real user class that will be instantiated and run by Locust
# This is the only thing that is actually specific to the service that we are
# testing.
class ExampleRsyncUser(RsyncUser):
    """Example rsync user for [self.host]."""

    host = "rpki.ripe.net"
    temp_dir = tempfile.TemporaryDirectory(prefix="locust-plugin-rsync")

    @task
    def get_ta_cert(self):
        """Retrieve trust anchor certificate."""
        self.client.get("ta/RIPE-NCC-TA-TEST.cer")

    @task
    def get_repo(self):
        """Copy the full repository."""
        self.client.get("repository")


if __name__ == "__main__":
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)

    LOG = logging.getLogger(__name__)

    with open("enable_gevent_debugging.py", "r") as myfile:
        LOG.info("Enabling remote debugging - waiting for client to connect.")
        exec(myfile.read())  # pylint: disable=W0122

    run_single_user(ExampleRsyncUser)
