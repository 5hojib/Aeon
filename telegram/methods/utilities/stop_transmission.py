import telegram


class StopTransmission:
    @staticmethod
    def stop_transmission():
        raise telegram.StopTransmission
