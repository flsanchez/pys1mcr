from icon import IconSet

KB = 1024


class MemoryCard:
  def __init__(self, path):
    self._path = path
    self._load_file_contents()
    self._blocks = None
    self._generate_blocks()

  def _load_file_contents(self):
    expected_file_bytes_size = 128*KB
    with open(self._path, 'rb') as f:
      file_contents = f.read()
    if self._path.endswith(".gme"):
      file_contents = file_contents[0xF40:]
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

  def plot_icons_for_block(self, block_number, save=False):
    for icon in self._blocks[block_number]._icon_set._icons:
      icon.plot_icon(save)

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
    self._icon_set = None
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
    raw_color_palette = self._frames[0]._frame_data[0x60:0x80]
    number_of_icons = self._frames[0]._frame_data[0x02] & 0b1111
    icon_set = IconSet(raw_color_palette)
    icons_frames = self._frames[1:(1+number_of_icons)]
    for icon_frame in icons_frames:
      icon_set.generate_icon_from_data(icon_frame._frame_data)
    self._icon_set = icon_set


class Frame:
  def __init__(self, frame_data):
    self._frame_data = frame_data


if __name__ == "__main__":
  #path = "data/ff-vii.mcd"
  path = "data/mixed_data.mcd"
  #path = "data/a.mc"
  mc = MemoryCard(path)
  block_number = 1
  print(mc.get_block_title(block_number))
  mc.plot_icons_for_block(block_number)
