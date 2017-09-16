"""
I am a self-contained program!
"""

import mitogen.master


def repr_stuff():
    return repr([__name__, 50])


def main():
    broker = mitogen.master.Broker()
    try:
        context = mitogen.master.connect(broker)
        print context.call(repr_stuff)
    finally:
        broker.shutdown()
        broker.join()

if __name__ == '__main__' and mitogen.is_master:
    main()
