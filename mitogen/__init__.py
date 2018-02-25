# Copyright 2017, David Wilson
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
# list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
# may be used to endorse or promote products derived from this software without
# specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
On the Mitogen master, this is imported from ``mitogen/__init__.py`` as would
be expected. On the slave, it is built dynamically during startup.
"""

#: This is ``False`` in slave contexts. It is used in single-file Python
#: programs to avoid reexecuting the program's :py:func:`main` function in the
#: slave. For example:
#:
#:      .. code-block:: python
#:
#:          def do_work():
#:              os.system('hostname')
#:
#:          def main(broker):
#:              context = mitogen.master.connect(broker)
#:              context.call(do_work)  # Causes slave to import __main__.
#:
#:          if __name__ == '__main__' and mitogen.is_master:
#:              import mitogen.utils
#:              mitogen.utils.run_with_broker(main)
#:
is_master = True


#: This is ``0`` in a master, otherwise it is a master-generated ID unique to
#: the slave context used for message routing.
context_id = 0


#: This is ``None`` in a master, otherwise it is the master-generated ID unique
#: to the slave's parent context.
parent_id = None


#: This is an empty list in a master, otherwise it is a list of parent context
#: IDs ordered from most direct to least direct.
parent_ids = []


def main(log_level='INFO'):
    """
    Convenience decorator primarily useful for writing discardable test scripts.

    In the master process, when `func` is defined in the ``__main__`` module,
    arranges for `func(router)` to be invoked immediately, with
    :py:class:`mitogen.master.Router` construction and destruction handled just
    as in :py:func:`mitogen.utils.run_with_router`. In slaves, this function
    does nothing.

    :param str log_level:
        Logging package level to configure via
        :py:func:`mitogen.utils.log_to_file`.

    Example:

    ::

        import mitogen
        import requests

        def get_url(url):
            return requests.get(url).text

        @mitogen.main()
        def main(router):
            z = router.ssh(hostname='k3')
            print z.call(get_url, 'http://www.google.com/')

    """

    def wrapper(func):
        if func.__module__ != '__main__':
            return func
        from mitogen import utils
        utils.log_to_file(level=log_level)
        return utils.run_with_router(func)
    return wrapper
