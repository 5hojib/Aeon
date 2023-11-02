from .object import Object


class List(list):
    __slots__ = []

    def __str__(self):
        return Object.__str__(self)

    def __repr__(self):
        return f"telegram.types.List([{','.join(Object.__repr__(i) for i in self)}])"
