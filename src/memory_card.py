class MemoryCard:
    def __init__(self, path):
        self.path = path
        with open(path, 'rb') as f:
            self.file_contents = f.read()


class Block:
    


if __name__ == "__main__":
    path = "data/a.mc"
    mc = MemoryCard(path)
    print(mc)