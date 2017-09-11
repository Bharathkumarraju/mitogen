
import logging
import os
import pty
import termios
import time

import mitogen.core
import mitogen.master


LOG = logging.getLogger(__name__)
PASSWORD_PROMPT = 'password'


class PasswordError(mitogen.core.Error):
    pass


def flags(names):
    """Return the result of ORing a set of (space separated) :py:mod:`termios`
    module constants together."""
    return sum(getattr(termios, name) for name in names.split())


def cfmakeraw((iflag, oflag, cflag, lflag, ispeed, ospeed, cc)):
    """Given a list returned by :py:func:`termios.tcgetattr`, return a list
    that has been modified in the same manner as the `cfmakeraw()` C library
    function."""
    iflag &= ~flags('IGNBRK BRKINT PARMRK ISTRIP INLCR IGNCR ICRNL IXON')
    oflag &= ~flags('OPOST IXOFF')
    lflag &= ~flags('ECHO ECHOE ECHONL ICANON ISIG IEXTEN')
    cflag &= ~flags('CSIZE PARENB')
    cflag |= flags('CS8')

    iflag = 0
    oflag = 0
    lflag = 0
    return [iflag, oflag, cflag, lflag, ispeed, ospeed, cc]


def disable_echo(fd):
    old = termios.tcgetattr(fd)
    new = cfmakeraw(old)
    flags = (
        termios.TCSAFLUSH |
        getattr(termios, 'TCSASOFT', 0)
    )
    termios.tcsetattr(fd, flags, new)


def close_nonstandard_fds():
    for fd in xrange(3, 1024):
        try:
            os.close(fd)
        except OSError:
            pass


def tty_create_child(*args):
    """
    Return a file descriptor connected to the master end of a pseudo-terminal,
    whose slave end is connected to stdin/stdout/stderr of a new child process.
    The child is created such that the pseudo-terminal becomes its controlling
    TTY, ensuring access to /dev/tty returns a new file descriptor open on the
    slave end.

    :param args:
        execl() arguments.
    """
    master_fd, slave_fd = os.openpty()
    disable_echo(master_fd)
    disable_echo(slave_fd)

    pid = os.fork()
    if not pid:
        os.dup2(slave_fd, 0)
        os.dup2(slave_fd, 1)
        os.dup2(slave_fd, 2)
        close_nonstandard_fds()
        os.setsid()
        os.close(os.open(os.ttyname(1), os.O_RDWR))
        os.execvp(args[0], args)
        raise SystemExit

    os.close(slave_fd)
    LOG.debug('tty_create_child() child %d fd %d, parent %d, args %r',
              pid, master_fd, os.getpid(), args)
    return pid, master_fd


class Stream(mitogen.master.Stream):
    create_child = staticmethod(tty_create_child)
    sudo_path = 'sudo'
    password = None

    def construct(self, username=None, sudo_path=None, password=None, **kwargs):
        """
        Get the named sudo context, creating it if it does not exist.

        :param mitogen.core.Broker broker:
            The broker that will own the context.

        :param str username:
            Username to pass to sudo as the ``-u`` parameter, defaults to ``root``.

        :param str sudo_path:
            Filename or complete path to the sudo binary. ``PATH`` will be searched
            if given as a filename. Defaults to ``sudo``.

        :param str python_path:
            Filename or complete path to the Python binary. ``PATH`` will be
            searched if given as a filename. Defaults to :py:data:`sys.executable`.

        :param str password:
            The password to use when authenticating to sudo. Depending on the sudo
            configuration, this is either the current account password or the
            target account password. :py:class:`mitogen.sudo.PasswordError` will
            be raised if sudo requests a password but none is provided.

        """
        super(Stream, self).construct(**kwargs)
        self.username = username or 'root'
        if sudo_path:
            self.sudo_path = sudo_path
        if password:
            self.password = password
        self.name = 'sudo.' + self.username

    def get_boot_command(self):
        bits = [self.sudo_path, '-u', self.username]
        bits = bits + super(Stream, self).get_boot_command()
        LOG.debug('sudo command line: %r', bits)
        return bits

    password_incorrect_msg = 'sudo password is incorrect'
    password_required_msg = 'sudo password is required'

    def _connect_bootstrap(self):
        password_sent = False
        for buf in mitogen.master.iter_read(self.receive_side.fd,
                                             time.time() + 10.0):
            LOG.debug('%r: received %r', self, buf)
            if buf.endswith('EC0\n'):
                return self._ec0_received()
            elif PASSWORD_PROMPT in buf.lower():
                if self.password is None:
                    raise PasswordError(self.password_required_msg)
                if password_sent:
                    raise PasswordError(self.password_incorrect_msg)
                LOG.debug('sending password')
                os.write(self.transmit_side.fd, self.password + '\n')
                password_sent = True
        else:
            raise mitogen.core.StreamError('bootstrap failed')
