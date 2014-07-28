import uuid

class IdGenerator:
    def getId(self):
        return str(uuid.uuid4()).replace('-', '')
    