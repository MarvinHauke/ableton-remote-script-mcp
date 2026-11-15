class ModelObject(object):
    pass


class ValueProperty(object):
    def __init__(self, writeable=True):
        self.writeable = writeable
