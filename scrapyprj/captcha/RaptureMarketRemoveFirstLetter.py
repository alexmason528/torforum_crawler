import logging


class RaptureMarketRemoveFirstLetter(object):
    def __init__(self):
        self.logger = logging.getLogger('RaptureMarketRemoveFirstLetter')

    def process(self, data):
        if data:
            data = data[-5:]

        return data
