class EveDataResolutionError(Exception):
    """
    Thrown when we failed to resolve something using the static database or ESI
    This should not happen, it usually means that we have a fatal problem in our code OR CCP has an issue with ESI or the static export. 
    """
    def __init__(self, msg):
        self.msg = msg

class EveMissingScopeException(Exception):
    """
    Thrown when we make a call without a proper token. 
    """
    def __init__(self, msg):
        self.msg = msg 