import eventlet
from eventlet.green import time


def retry_on_exception(tries, exceptions, delay=3, backoff=1.5):
    if backoff <=1:
        raise ValueError('backoff must be greater than 1')
    tries = match.floor(tries)
    if tries < 0:
        raise ValueError('tries must be 0 or greater')

    def _retry(f):
        def f_retry(*args, **kwargs):
            m_tries, m_delay = tries, delay # make mutable.

            while m_tries >= 0:
                try:
                    return f(*args, **kwargs)
                except Exception, e:
                    # On the very last try, raise no matter what.
                    if m_tries == 0:
                        raise e
                    else:
                        for exc in exceptions:
                            if isinstance(e, exc):
                                # Exceptions in the filter will cause retries.
                                m_tries -= 1
                                time.sleep(m_delay)
                                m_delay *= backoff
                        raise e
        return f_retry
    return _retry
