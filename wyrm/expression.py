# Temp
class Expression:
    def __init__(self):
        pass

    def evaluate(self, *contexts):
        return

class String(Expression):
    def __init__(self, string):
        self.string = string

    def evaluate(self, *contexts):
        return self.string

def evaluate(string, *contexts):
    return string
