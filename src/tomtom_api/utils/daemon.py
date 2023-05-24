"""
Daemon base class

Research on how to properly create and handle daemon processes can bring someone to look for the following resources:
- https://peps.python.org/pep-3143/
    - https://stackoverflow.com/questions/23515165/correct-daemon-behaviour-from-pep-3143-explained
    - https://stackoverflow.com/questions/881388/what-is-the-reason-for-performing-a-double-fork-when-creating-a-daemon
- https://stackoverflow.com/questions/473620/how-do-you-create-a-daemon-in-python

The following code is vastly inspired and/or shamelessly copied from this link (glory to the wayback machine!)
https://web.archive.org/web/20131017130434/http://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python/
"""

import atexit
import os
import sys
import time
from pathlib import Path
from signal import SIGTERM
from typing import Optional


class Daemon:
    """
    A generic daemon class.

    Usage: subclass the Daemon class and override the run() method
    """

    def __init__(
        self,
        pid_file: Path,
        stdin: Path = Path('/dev/null'),
        stdout: Path = Path('/dev/null'),
        stderr: Path = Path('/dev/null')
    ):
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.pid_file = pid_file

    def daemonize(self):
        """
        do the UNIX double-fork magic, see Stevens' "Advanced
        Programming in the UNIX Environment" for details (ISBN 0201563177)
        http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
        """
        try:
            pid = os.fork()
            if pid > 0:
                # exit first parent
                sys.exit(0)
        except OSError as e:
            sys.stderr.write(f"fork #1 failed: {e.errno} ({e})\n")
            sys.exit(1)

        # decouple from parent environment
        os.chdir("/")
        os.setsid()
        os.umask(0)

        # do second fork
        try:
            pid = os.fork()
            if pid > 0:
                # exit from second parent
                sys.exit(0)
        except OSError as e:
            sys.stderr.write(f"fork #2 failed: failed: {e.errno} ({e})\n")
            sys.exit(1)

        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = open(self.stdin, 'r')
        so = open(self.stdout, 'a+')
        se = open(self.stderr, 'ab+', 0)
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        # write pid file
        atexit.register(self.delete_pid)
        open(self.pid_file, 'w+').write(f"{os.getpid()}\n")

    def delete_pid(self):
        os.remove(self.pid_file)

    def start(self):
        """
        Start the daemon
        """
        # Check for a pid file to see if the daemon already runs
        try:
            pf = open(self.pid_file, 'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None

        if pid:
            message = f"pid file {self.pid_file} already exist. Daemon already running?\n"
            sys.stderr.write(message)
            sys.exit(1)

        # Start the daemon
        self.daemonize()
        self.run()

    def stop(self):
        """
        Stop the daemon
        """
        # Get the pid from the pid file
        pid = self.get_pid(True)

        if pid is None:
            message = f"pid file {self.pid_file} does not exist. Daemon not running?\n"
            sys.stderr.write(message)
            return  # not an error in a restart

        # Try killing the daemon process
        try:
            while 1:
                os.kill(pid, SIGTERM)
                time.sleep(0.1)
        except OSError as err:
            err = str(err)
            if err.find("No such process") > 0:
                if os.path.exists(self.pid_file):
                    os.remove(self.pid_file)
            else:
                sys.stderr.write(str(err))
                sys.exit(1)

    def restart(self):
        """
        Restart the daemon
        """
        self.stop()
        self.start()

    def get_pid(self, nice: bool = False) -> Optional[int]:
        try:
            pf = open(self.pid_file, 'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError as e:
            if not nice:
                raise e
            else:
                pid = None
        return pid

    def is_alive(self) -> bool:
        pid = self.get_pid(True)
        if pid is None:
            return False

        # Sending signal 0 to a pid will raise an OSError exception if the pid is not running, and do nothing otherwise.
        # source: https://stackoverflow.com/questions/568271/how-to-check-if-there-exists-a-process-with-a-given-pid-in-python
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        else:
            return True

    def status(self):
        name = 'Tomtom API priority queue daemon'
        state = "RUNNING" if self.is_alive() else "STOPPED"
        return f'{name} is {state}.'

    def run(self):
        """
        You should override this method when you subclass Daemon. It will be called after the process has been
        daemonized by start() or restart().
        """
        pass
