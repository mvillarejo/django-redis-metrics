"""
A command to record system metrics (CUP, Memory, Disk usage). Run this as a
cron job to periodically caputes sysem resource usage. Requires psutil.

Usage:

    manage.py system_metric <metric> [device|interface] [category]

Examples:

    manage.py system_metric cpu -- Records total CPU usage as a percent
    manage.py system_metric mem -- Records virtual memory used as a percent
    manage.py system_metric disk sda1 -- Records percent usage of device sda1
    manage.py system_metric net eth0 -- Records bytest sent/received on
        interface eth0

"""
from django.core.management.base import BaseCommand, CommandError
from redis_metrics.utils import metric

try:
    import psutil
except ImportError:
    psutil = None  # NOQA


class Command(BaseCommand):
    args = '<metric_name> [dev|interface] [category]'
    help = """Record System Metrics. Valid metric_name values: cpu, mem, disk.

    USAGE:

    To record CPU usage (percent used), run:

        manage.py system_metric cp

    To record Memory usage (virtual memory, percent used), run:

        manage.py system_metric mem

    To record Disk usage for a device, run:

        manage.py system_metric disk <device>

    for example:

        mange.py system_metric disk sda0

    To record Network usage for an interface, run:

        manage.py system_metric disk <device>

    for example:

        mange.py system_metric net eth0


    """

    def process_args(self, *args):

        self.category = "System"
        self.metric_name = None
        self.device = None

        if len(args) == 1 and args[0] in ['cpu', 'mem']:
            self.metric_name = args[0]
        if len(args) == 2 and args[0] in ['cpu', 'mem']:
            self.metric_name = args[0]
            self.category = args[1].strip()
        elif len(args) == 2 and args[0] in ['disk', 'net']:
            self.metric_name = args[0]
            self.device = args[1]
        elif len(args) == 3 and args[0] in ['disk', 'net']:
            self.metric_name = args[0]
            self.device = args[1]
            self.category = args[2].strip()
        else:
            raise CommandError("Invalid Arugments. Plase run "
                "`manage.py help system_metric`")

    def handle(self, *args, **options):
        # Make sure we've got psutil
        if psutil is None:
            raise CommandError("This command requires psutil")

        self.process_args(*args)

        if self.metric_name == "cpu":
            metric(int(psutil.cpu_percent()), category=self.category)
        elif self.metric_name == "mem":
            metric(
                int(psutil.virtual_memory().percent),
                category=self.category
            )
        elif self.metric_name == "disk":
            mountpoints = [
                p.mountpoint for p in psutil.disk_partitions()
                if p.devicde.endswith(self.device)
            ]
            if len(self.mountpoints) != 1:
                raise CommandError("Unknown device: {0}".format(self.device))
            metric_name = "disk-{0}".format(self.device)
            metric(
                metric_name,
                int(psutil.disk_usage(mountpoints[0]).percent),
                category=self.category
            )
        elif self.metric_name == "net":
            data = psutil.network_io_counters(pernic=True)
            if self.device not in data:
                raise CommandError("Unknown device: {0}".format(self.device))
            metric_name_sent = "net-{0}-sent".format(self.device)
            metric(
                metric_name_sent,
                data[self.device].bytes_sent,
                category=self.category
            )

            metric_name_recv = "net-{0}-recv".format(self.device)
            metric(
                metric_name_recv,
                data[self.device].bytes_recv,
                category=self.category
            )
        else:
            m = "{0} is an invalid metric_name".format(self.metric_name)
            raise CommandError(m)
