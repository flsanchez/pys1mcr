import numpy as np
import matplotlib.pyplot as plt

KB = 1024


class MemoryCard:
  def __init__(self, path):
    self._path = path
    self._load_file_contents()
    self._blocks = None
    self._generate_blocks()

  def _load_file_contents(self):
    expected_file_bytes_size = 128*KB
    with open(path, 'rb') as f:
      file_contents = f.read()
    if len(file_contents) != expected_file_bytes_size:
      raise Exception(
        f"Incompatible size: expecting {expected_file_bytes_size} bytes, got {len(file_contents)} bytes instead"
      )
    self._file_contents = file_contents

  def _block_generator(self):
    block = 0
    while block < 16:
      yield self._file_contents[block*8*KB:(block+1)*8*KB]
      block += 1

  def _generate_blocks(self):
    self._blocks = [
      Block(block_data) for block_data in self._block_generator()
    ]

  def plot_icon_1_for_block(self, block_number):
    # Hexa value (shift) indexed to the color palette (0 to F): Left nibble is the 2nd pixel.
    # ex: [0x4f, 0x9e] -> [f, 4, e, 9]
    color_map = np.array(list(mc._blocks[block_number]._frames[0]._frame_data[0x60:0x80])).reshape((16, 2))
    print([
      hex(color[0]//16*16**3+color[0]%16*16**2+color[1]) 
      for color in color_map
    ])
    icon_data = np.array([
      [pixel%16, pixel//16] for pixel in list(mc._blocks[block_number]._frames[1]._frame_data)
    ]).reshape((16, 16))
    plt.imshow(icon_data, cmap='binary')
    plt.show()

  def get_block_title(self, block_number):
    try:
      title = self._blocks[block_number]._frames[0]._frame_data[0x04:(0x04+64)].decode('shift-jis')
    except UnicodeDecodeError:
      title = self._blocks[block_number]._frames[0]._frame_data[0x04:(0x04+32)].decode('shift-jis')
    return title


class Block:
  def __init__(self, block_data):
    self._block_data = block_data
    self._frames = None
    self._generate_frames()

  def _frame_generator(self):
    frame = 0
    while frame < 64:
      yield self._block_data[frame*128:(frame+1)*128]
      frame += 1

  def _generate_frames(self):
    self._frames = [
      Frame(frame_data) for frame_data in self._frame_generator()
    ]


class Frame:
  def __init__(self, frame_data):
    self._frame_data = frame_data


if __name__ == "__main__":
  #path = "data/ff-vii.mcd"
  path = "data/a.mc"
  mc = MemoryCard(path)
  block_number = 1
  print(mc.get_block_title(block_number))
  mc.plot_icon_1_for_block(block_number)