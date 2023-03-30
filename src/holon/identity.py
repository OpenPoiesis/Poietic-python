from typing import TypeAlias
ID: TypeAlias = int

class SequentialIDGenerator:
    current: ID
    used: set[ID]

    def __init__(self):
        self.current = 0
        self.used = set()

    def next(self) -> int:
        while self.current in self.used:
            self.used.remove(self.current)
            self.current += 1
        id = self.current
        self.current += 1
        return id

    def mark_used(self, id: ID):
        self.used.add(id)



