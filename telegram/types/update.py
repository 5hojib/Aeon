import telegram


class Update:
    @staticmethod
    def stop_propagation():
        raise telegram.StopPropagation

    @staticmethod
    def continue_propagation():
        raise telegram.ContinuePropagation
