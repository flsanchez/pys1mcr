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
    color_map = np.array(
      list(self._blocks[block_number]._frames[0]._frame_data[0x60:0x80])
    ).reshape((16, 2))
    # color map little endian [0xff, 0x7f] -> 0x7fff
    color_map_16b = [
      color[1]//16*16**3+color[1]%16*16**2+color[0]
      for color in color_map
    ]
    
    # color map to rgb
    def transform_to_rgb(color):
    # 0-4   Red       (0..31)         ;\Color 0000h        = Fully-Transparent
    # 5-9   Green     (0..31)         ; Color 0001h..7FFFh = Non-Transparent
    # 10-14 Blue      (0..31)         ; Color 8000h..FFFFh = Semi-Transparent (*)
    # 15    Semi Transparency Flag    ;/(*) or Non-Transparent for opaque commands
      rgb = []
      for _ in range(0,3):
        rgb.append(color & (0b11111))
        color = color >> 5
      return np.array(rgb)/31

    color_map_rgb = [transform_to_rgb(color) for color in color_map_16b]
    icon_data = np.concatenate([
      [pixel%16, pixel//16] for pixel in list(mc._blocks[block_number]._frames[1]._frame_data)
    ])
    icon_data_rgb = np.array(
      [color_map_rgb[pixel_value] for pixel_value in icon_data]
    ).reshape((16, 16, 3))

    plt.axis('off')
    plt.imshow(icon_data_rgb)
    plt.savefig('icon.png', bbox_inches='tight')

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
    self._icons = None
    self._generate_icons()

  def _frame_generator(self):
    frame = 0
    while frame < 64:
      yield self._block_data[frame*128:(frame+1)*128]
      frame += 1

  def _generate_frames(self):
    self._frames = [
      Frame(frame_data) for frame_data in self._frame_generator()
    ]

  def _generate_icons(self):
    pass


class Frame:
  def __init__(self, frame_data):
    self._frame_data = frame_data


class Icon:
  def __init__(self, icon_data, color_palette):
    pass


if __name__ == "__main__":
  path = "data/ff-vii.mcd"
  #path = "data/a.mc"
  mc = MemoryCard(path)
  block_number = 1
  print(mc.get_block_title(block_number))
  mc.plot_icon_1_for_block(block_number)