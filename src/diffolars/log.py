import sys
from functools import wraps

# This is a simple decorator that redefines stdout to a file.
# To be able to pass filepath, I needed to add a middle nested layer (def decorator),
# which contains the wrapper. 
def logfile(filepath):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            original_stdout = sys.stdout
            with open(filepath, 'w') as f:
                sys.stdout = f
                try:
                    return func(*args, **kwargs)
                finally:
                    sys.stdout = original_stdout
        return wrapper
    return decorator